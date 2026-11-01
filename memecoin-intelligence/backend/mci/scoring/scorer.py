"""0-100 scoring with per-feature explanations.

Weights (revised from the initial proposal, see docs/SCORING.md):

=====================================  ======
Momentum e price action                  15
Volume e attività di mercato             15
Liquidità e possibilità di uscita        20
Analisi on-chain e wallet                20
Community e sentiment                    10
Età e caratteristiche del progetto        5
Rischio contrattuale e sicurezza         15
=====================================  ======

Rules:
* a feature whose input is missing scores 0 and is reported as "non disponibile";
* ``coverage`` = share of the 100 points whose inputs were available;
* hard filters (``filters.py``) override everything: excluded => label SCARTATO.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from mci.domain import Candle, ScoreResult, TokenSnapshot
from mci.scoring.filters import FilterConfig, evaluate_filters
from mci.social_analysis.analyzer import assess_attention
from mci.strategies.indicators import trend_up

CATEGORY_WEIGHTS = {
    "momentum": 15,
    "volume": 15,
    "liquidity": 20,
    "onchain": 20,
    "community": 10,
    "age": 5,
    "security": 15,
}

CATEGORY_LABELS = {
    "momentum": "Momentum e price action",
    "volume": "Volume e attività",
    "liquidity": "Liquidità e uscita",
    "onchain": "On-chain e wallet",
    "community": "Community e sentiment",
    "age": "Età e progetto",
    "security": "Sicurezza contratto",
}


@dataclass
class FeatureScore:
    name: str
    max_points: float
    points: float = 0.0
    available: bool = False
    note: str = ""


@dataclass
class _Cat:
    key: str
    features: list[FeatureScore] = field(default_factory=list)

    def add(self, name: str, max_points: float, value: Any, fn: Callable[[Any], tuple[float, str]]) -> None:
        f = FeatureScore(name, max_points)
        if value is None:
            f.note = "dato non disponibile"
        else:
            frac, note = fn(value)
            f.points = round(max(0.0, min(1.0, frac)) * max_points, 2)
            f.available = True
            f.note = note
        self.features.append(f)

    @property
    def points(self) -> float:
        return sum(f.points for f in self.features)

    @property
    def available_max(self) -> float:
        return sum(f.max_points for f in self.features if f.available)


def _band(value: float, bands: Sequence[tuple[float, float]]) -> float:
    """Return the fraction for the first band whose threshold is satisfied (descending)."""
    for threshold, frac in bands:
        if value >= threshold:
            return frac
    return 0.0


def score_token(
    s: TokenSnapshot,
    candles: Sequence[Candle] | None = None,
    filter_cfg: FilterConfig | None = None,
    for_trading: bool = False,
) -> ScoreResult:
    risks: list[str] = []
    expl: list[str] = []
    cats = {k: _Cat(k) for k in CATEGORY_WEIGHTS}

    # ---------------- 1. momentum (15) ----------------
    c = cats["momentum"]
    h1 = s.price_change_pct.get("h1")

    def f_h1(v: float) -> tuple[float, str]:
        if v > 300:
            risks.append(f"estensione eccessiva: +{v:.0f}% in 1h (rischio di inversione)")
            return 0.0, f"+{v:.0f}% in 1h: troppo esteso"
        if v >= 10:
            return (1.0 if v <= 150 else 0.6), f"{v:+.0f}% in 1h"
        if v >= 0:
            return 0.4, f"{v:+.1f}% in 1h (debole)"
        return 0.0, f"{v:+.1f}% in 1h (negativo)"

    c.add("variazione 1h", 5, h1, f_h1)
    c.add(
        "variazione 5m",
        3,
        s.price_change_pct.get("m5"),
        lambda v: ((1.0 if 0 <= v <= 25 else 0.3 if 25 < v <= 60 else 0.0), f"{v:+.1f}% in 5m"),
    )
    h6, h24 = s.price_change_pct.get("h6"), s.price_change_pct.get("h24")
    c.add(
        "trend 6h/24h",
        3,
        h6 if h6 is not None else h24,
        lambda v: ((1.0 if v > 0 else 0.0), f"{v:+.0f}% su orizzonte lungo"),
    )
    tu = trend_up(candles) if candles else None
    c.add("trend EMA20>EMA50", 4, tu, lambda v: ((1.0 if v else 0.0), "EMA veloce sopra lenta" if v else "trend non confermato"))

    # ---------------- 2. volume (15) ----------------
    c = cats["volume"]
    discount = 1.0
    if s.wash_score is not None:
        discount = max(0.0, 1.0 - s.wash_score)
    vol_h1 = s.vol("h1")
    liq = s.liquidity_usd
    turnover = (vol_h1 * discount / liq) if (vol_h1 is not None and liq) else None
    c.add(
        "turnover 1h (volume scontato/liquidità)",
        5,
        turnover,
        lambda v: (_band(v, [(0.3, 1.0), (0.1, 0.5)]) if v <= 8 else 0.4, f"turnover {v:.2f}x"),
    )
    vm5 = s.vol("m5")
    accel = (vm5 * 12 / vol_h1) if (vm5 is not None and vol_h1) else None
    c.add("accelerazione volume (5m vs 1h)", 4, accel, lambda v: (_band(v, [(1.5, 1.0), (1.1, 0.6), (0.8, 0.25)]), f"accelerazione {v:.2f}x"))
    b, se = s.buys.get("h1"), s.sells.get("h1")
    ratio = (b / (b + se)) if (b is not None and se is not None and (b + se) > 0) else None

    def f_ratio(v: float) -> tuple[float, str]:
        if v > 0.85:
            risks.append(f"rapporto buy/sell anomalo ({v:.2f}): possibile volume artificiale")
            return 0.2, f"buy ratio {v:.2f} sospetto"
        return (1.0 if 0.52 <= v <= 0.75 else 0.5 if v > 0.75 else 0.0), f"buy ratio {v:.2f}"

    c.add("rapporto acquisti/vendite 1h", 3, ratio, f_ratio)
    by5, by1 = s.buyers.get("m5"), s.buyers.get("h1")
    growth = (by5 * 12 / by1) if (by5 is not None and by1) else None
    c.add(
        "crescita compratori unici",
        3,
        growth if (by1 or 0) >= 30 else (None if by1 is None else 0.0),
        lambda v: (_band(v, [(1.3, 1.0), (1.0, 0.6), (0.7, 0.2)]), f"compratori unici {by1} in 1h, ritmo {v:.2f}x"),
    )

    # ---------------- 3. liquidity (20) ----------------
    c = cats["liquidity"]
    c.add("liquidità assoluta", 8, liq, lambda v: (_band(v, [(150_000, 1.0), (75_000, 0.85), (30_000, 0.6), (15_000, 0.3)]), f"{v:,.0f} $"))
    mc = s.market_cap_usd or s.fdv_usd
    lr = (liq / mc) if (liq and mc) else None

    def f_lr(v: float) -> tuple[float, str]:
        if v < 0.03:
            risks.append(f"liquidità bassa rispetto alla market cap ({v:.1%})")
        return _band(v, [(0.08, 1.0), (0.04, 0.6), (0.03, 0.3)]), f"liquidità/MC {v:.1%}"

    c.add("liquidità / market cap", 5, lr, f_lr)
    c.add(
        "impatto di vendita (quote reale)",
        7,
        s.sell_impact_pct,
        lambda v: (_band(-v, [(-1.0, 1.0), (-2.0, 0.7), (-3.0, 0.4)]), f"impatto {v:.2f}% per {s.quote_probe_sol or 0:.2f} SOL"),
    )

    # ---------------- 4. on-chain (20) ----------------
    c = cats["onchain"]

    def f_top10(v: float) -> tuple[float, str]:
        if v > 30:
            risks.append(f"concentrazione dei wallet: top 10 = {v:.1f}%")
        return _band(-v, [(-15, 1.0), (-22, 0.7), (-30, 0.4)]), f"top 10 holder {v:.1f}%"

    c.add("concentrazione top 10", 7, s.top10_pct, f_top10)
    c.add("numero holder", 4, s.holders_count, lambda v: (_band(v, [(2000, 1.0), (500, 0.75), (200, 0.5), (100, 0.25)]), f"{v:,} holder"))
    c.add("quota deployer", 3, s.dev_pct, lambda v: (_band(-v, [(-1, 1.0), (-3, 0.66), (-5, 0.33)]), f"deployer {v:.1f}%"))
    cluster = None
    if s.insider_cluster_pct is not None or s.early_buyer_cluster_pct is not None:
        cluster = max(s.insider_cluster_pct or 0.0, s.early_buyer_cluster_pct or 0.0)

    def f_cluster(v: float) -> tuple[float, str]:
        if v > 10:
            risks.append(f"cluster insider/sniper con il {v:.1f}% della supply")
        return _band(-v, [(-5, 1.0), (-10, 0.5)]), f"cluster insider/sniper {v:.1f}%"

    c.add("insider / bundle", 3, cluster, f_cluster)

    def f_wash(v: float) -> tuple[float, str]:
        if v > 0.4:
            risks.append(f"possibile wash trading (score {v:.2f})")
        return _band(-v, [(-0.2, 1.0), (-0.4, 0.5)]), f"wash score {v:.2f}"

    c.add("qualità del volume (wash)", 3, s.wash_score, f_wash)

    # ---------------- 5. community (10) ----------------
    c = cats["community"]
    soc = s.socials or {}
    present = sum(1 for k in ("twitter", "telegram", "website") if soc.get(k))
    c.add("presenza social", 3, present if (s.has_profile is not None or soc) else None, lambda v: (v / 3, f"{v}/3 canali dichiarati"))
    att = assess_attention(s)
    att_frac = {"organic": 1.0, "paid_marketing": 0.25}.get(att.category, 0.0)
    if att.category in ("artificial", "coordinated", "suspicious"):
        risks.append(f"attenzione di tipo '{att.category}': " + "; ".join(att.evidence))
    c.add(
        "tipo di attenzione (organica vs artificiale)",
        4,
        None if att.category == "unknown" else att.category,
        lambda v: (att_frac, f"{v}: " + "; ".join(att.evidence)),
    )
    reddit = (s.social_metrics or {}).get("reddit")
    c.add(
        "menzioni Reddit (autori unici 24h)",
        3,
        (reddit or {}).get("unique_authors") if isinstance(reddit, dict) else None,
        lambda v: (_band(v, [(10, 1.0), (5, 0.6), (2, 0.2)]), f"{v} autori unici"),
    )

    # ---------------- 6. age (5) ----------------
    c = cats["age"]
    age = s.age_minutes

    def f_age(v: float) -> tuple[float, str]:
        if v < 30:
            return 0.2, f"{v:.0f} min (molto giovane)"
        if v < 24 * 60:
            return 0.6, f"{v / 60:.1f} h"
        if v < 7 * 24 * 60:
            return 1.0, f"{v / 1440:.1f} giorni"
        return 0.8, f"{v / 1440:.0f} giorni"

    c.add("età del token", 3, age, f_age)
    c.add(
        "fase (bonding curve / DEX)",
        2,
        s.bonding_curve,
        lambda v: ((0.3, "ancora su bonding curve") if v else (1.0, "migrato su DEX")),
    )

    # ---------------- 7. security (15) ----------------
    c = cats["security"]
    c.add("mint authority revocata", 4, s.mint_authority_revoked, lambda v: ((1.0, "revocata") if v else (0.0, "ATTIVA")))
    c.add("freeze authority revocata", 4, s.freeze_authority_revoked, lambda v: ((1.0, "revocata") if v else (0.0, "ATTIVA")))
    c.add("punteggio RugCheck", 3, s.rugcheck_score_norm, lambda v: (_band(-v, [(-30, 1.0), (-50, 0.5)]), f"{v:.0f}/100 (più basso = meglio)"))
    has_sec = "security" in s.sources
    n_danger = sum(1 for r in s.rugcheck_risks if r.get("level") == "danger")
    n_warn = sum(1 for r in s.rugcheck_risks if r.get("level") == "warn")
    c.add(
        "rischi segnalati",
        2,
        (n_danger, n_warn) if has_sec else None,
        lambda v: ((1.0 if v[0] == 0 and v[1] == 0 else 0.5 if v[0] == 0 else 0.0), f"{v[0]} critici, {v[1]} avvisi"),
    )
    lp_ok: Any = None
    if s.bonding_curve or (s.dex_id or "") in ("pumpfun", "pump", "pumpswap"):
        lp_ok = 100.0
    elif s.lp_locked_pct is not None:
        lp_ok = s.lp_locked_pct
    c.add("LP bloccata / bruciata", 2, lp_ok, lambda v: (_band(v, [(90, 1.0), (50, 0.4)]), f"{v:.0f}%"))

    # ---------------- aggregate ----------------
    total = round(sum(cat.points for cat in cats.values()), 1)
    coverage = round(sum(cat.available_max for cat in cats.values()) / 100.0, 3)
    filt = evaluate_filters(s, filter_cfg, for_trading=for_trading)
    if for_trading:
        for crit in ("liquidity", "security"):
            cov = cats[crit].available_max / CATEGORY_WEIGHTS[crit]
            if cov < 0.5 and "INSUFFICIENT_DATA" not in filt.codes:
                filt.codes.append("INSUFFICIENT_DATA")
                filt.reasons.append(f"copertura dati insufficiente nella categoria '{CATEGORY_LABELS[crit]}' ({cov:.0%})")
                filt.excluded = True

    categories: dict[str, dict[str, Any]] = {}
    for k, cat in cats.items():
        categories[k] = {
            "label": CATEGORY_LABELS[k],
            "points": round(cat.points, 1),
            "max": CATEGORY_WEIGHTS[k],
            "coverage": round(cat.available_max / CATEGORY_WEIGHTS[k], 2),
            "features": [f.__dict__.copy() for f in cat.features],
        }
        best = sorted((f for f in cat.features if f.available and f.points > 0), key=lambda f: -f.points)
        if best:
            expl.append(f"{CATEGORY_LABELS[k]}: {cat.points:.1f}/{CATEGORY_WEIGHTS[k]} — " + "; ".join(f.note for f in best[:2]))
        missing = [f.name for f in cat.features if not f.available]
        if missing:
            expl.append(f"{CATEGORY_LABELS[k]}: non disponibili → {', '.join(missing)}")

    if filt.excluded:
        label = "SCARTATO"
    elif total >= 80:
        label = "ALTO POTENZIALE"
    elif total >= 70:
        label = "INTERESSANTE"
    elif total >= 55:
        label = "OSSERVARE"
    else:
        label = "DEBOLE"
    if coverage < 0.6:
        risks.append(f"copertura dei dati bassa ({coverage:.0%}): punteggio prudenziale")

    return ScoreResult(
        total=total,
        categories=categories,
        coverage=coverage,
        excluded=filt.excluded,
        exclusion_reasons=filt.reasons,
        explanations=expl,
        risks=list(dict.fromkeys(risks)),
        label=label,
    )
