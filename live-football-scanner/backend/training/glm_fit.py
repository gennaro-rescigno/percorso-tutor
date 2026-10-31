"""Memory-efficient Poisson GLM (log link, offset) with cluster-robust covariance.

Newton-Raphson with step halving; X'WX and the gradient are accumulated in row chunks
so ~2M x 40 designs fit in well under 1 GB. Covariance is the sandwich estimator
clustered by match (rows from the same match are not independent), with the usual
small-sample correction G/(G-1) * (n-1)/(n-p).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln

CHUNK = 200_000


@dataclass
class PoissonFit:
    coef: np.ndarray
    cov: np.ndarray
    se: np.ndarray
    loglik: float
    deviance: float
    aic: float
    pearson_dispersion: float
    n: int
    iterations: int


def _eta(X: np.ndarray, beta: np.ndarray, offset: np.ndarray) -> np.ndarray:
    out = np.empty(X.shape[0])
    for i in range(0, X.shape[0], CHUNK):
        out[i:i + CHUNK] = X[i:i + CHUNK].astype(np.float64) @ beta + offset[i:i + CHUNK]
    return out


def _loglik(y: np.ndarray, eta: np.ndarray) -> float:
    return float(np.sum(y * eta - np.exp(eta)))


def fit_poisson(X: np.ndarray, y: np.ndarray, offset: np.ndarray, groups: np.ndarray,
                max_iter: int = 60, tol: float = 1e-7, ridge: float = 1e-8) -> PoissonFit:
    n, p = X.shape
    y = y.astype(np.float64)
    beta = np.zeros(p)
    # intercept start (column 0 must be the constant)
    beta[0] = np.log(max(y.sum(), 1e-9) / np.exp(offset).sum())
    eta = _eta(X, beta, offset)
    ll = _loglik(y, eta)
    it = 0
    for it in range(1, max_iter + 1):
        mu = np.exp(eta)
        grad = np.zeros(p)
        H = np.zeros((p, p))
        for i in range(0, n, CHUNK):
            Xi = X[i:i + CHUNK].astype(np.float64)
            r = y[i:i + CHUNK] - mu[i:i + CHUNK]
            grad += Xi.T @ r
            H += Xi.T @ (Xi * mu[i:i + CHUNK, None])
        step = np.linalg.solve(H + ridge * np.eye(p), grad)
        t = 1.0
        while True:
            nb = beta + t * step
            ne = _eta(X, nb, offset)
            nll = _loglik(y, ne)
            if nll >= ll - 1e-10 or t < 1e-6:
                break
            t *= 0.5
        beta, eta, ll_old, ll = nb, ne, ll, nll
        if np.max(np.abs(t * step)) < tol or abs(ll - ll_old) < 1e-9 * max(1.0, abs(ll)):
            break
    mu = np.exp(eta)
    # bread
    H = np.zeros((p, p))
    for i in range(0, n, CHUNK):
        Xi = X[i:i + CHUNK].astype(np.float64)
        H += Xi.T @ (Xi * mu[i:i + CHUNK, None])
    bread = np.linalg.inv(H + ridge * np.eye(p))
    # cluster meat
    _, gidx = np.unique(groups, return_inverse=True)
    G = int(gidx.max()) + 1
    U = np.zeros((G, p))
    for i in range(0, n, CHUNK):
        Xi = X[i:i + CHUNK].astype(np.float64)
        sc = Xi * (y[i:i + CHUNK] - mu[i:i + CHUNK])[:, None]
        np.add.at(U, gidx[i:i + CHUNK], sc)
    meat = U.T @ U
    corr = (G / (G - 1)) * ((n - 1) / (n - p))
    cov = corr * bread @ meat @ bread
    cov = 0.5 * (cov + cov.T)
    with np.errstate(divide="ignore", invalid="ignore"):
        dev_terms = np.where(y > 0, y * np.log(y / mu), 0.0) - (y - mu)
    deviance = float(2 * dev_terms.sum())
    loglik_full = float(np.sum(y * np.log(np.maximum(mu, 1e-300)) - mu - gammaln(y + 1)))
    pearson = float(np.sum((y - mu) ** 2 / mu) / (n - p))
    return PoissonFit(coef=beta, cov=cov, se=np.sqrt(np.clip(np.diag(cov), 0, None)), loglik=loglik_full,
                      deviance=deviance, aic=-2 * loglik_full + 2 * p, pearson_dispersion=pearson, n=n,
                      iterations=it)
