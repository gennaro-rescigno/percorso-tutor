"""Fitted hazard models (Poisson GLM, log link) and their serialisation.

A model artifact is a JSON file produced by ``training/train.py``. It contains,
for each sub-model, the feature names, the coefficient vector and the
cluster-robust covariance matrix (clustered by match), plus the population
reference rates and the empirical stoppage-time distributions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "inplay_model.json"


@dataclass
class GLM:
    name: str
    features: list[str]
    coef: np.ndarray
    cov: np.ndarray
    dispersion: float = 1.0  # NB dispersion (alpha) for count markets; 0 = Poisson
    meta: dict = field(default_factory=dict)

    def draws(self, n: int, rng: np.random.Generator) -> np.ndarray:
        """Coefficient draws (n, p). Row 0 is always the point estimate."""
        if n <= 1:
            return self.coef[None, :]
        cov = 0.5 * (self.cov + self.cov.T)
        # eigen-clip for numerical safety
        w, v = np.linalg.eigh(cov)
        w = np.clip(w, 0.0, None)
        L = v * np.sqrt(w)
        z = rng.standard_normal((n - 1, len(self.coef)))
        d = self.coef[None, :] + z @ L.T
        return np.vstack([self.coef[None, :], d])

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "features": self.features,
            "coef": self.coef.tolist(),
            "cov": self.cov.tolist(),
            "dispersion": self.dispersion,
            "meta": self.meta,
        }

    @classmethod
    def from_json(cls, d: dict) -> "GLM":
        return cls(
            name=d["name"],
            features=list(d["features"]),
            coef=np.asarray(d["coef"], dtype=float),
            cov=np.asarray(d["cov"], dtype=float),
            dispersion=float(d.get("dispersion", 1.0)),
            meta=d.get("meta", {}),
        )


@dataclass
class ModelBundle:
    version: str
    glms: dict[str, GLM]
    refs: dict[str, float]  # population per-90 per-team reference rates
    mu_goals: float  # mean goals per team per match (prior shrinkage target)
    prior_pseudo_matches: float
    stoppage: dict[str, list[float]]  # "h1"/"h2": P(added minutes = k), k=0..len-1
    validation: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def save(self, path: Path = DEFAULT_MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "glms": {k: g.to_json() for k, g in self.glms.items()},
            "refs": self.refs,
            "mu_goals": self.mu_goals,
            "prior_pseudo_matches": self.prior_pseudo_matches,
            "stoppage": self.stoppage,
            "validation": self.validation,
            "meta": self.meta,
        }
        path.write_text(json.dumps(payload, indent=1))

    @classmethod
    def load(cls, path: Path = DEFAULT_MODEL_PATH) -> "ModelBundle":
        d = json.loads(Path(path).read_text())
        return cls(
            version=d["version"],
            glms={k: GLM.from_json(v) for k, v in d["glms"].items()},
            refs=d["refs"],
            mu_goals=d["mu_goals"],
            prior_pseudo_matches=d["prior_pseudo_matches"],
            stoppage=d["stoppage"],
            validation=d.get("validation", {}),
            meta=d.get("meta", {}),
        )
