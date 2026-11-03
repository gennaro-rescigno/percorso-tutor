"""Separate, explainable RISK and OPPORTUNITY indices (0-100) + rule modes (enforce / shadow).

Honest by construction:

* they are INDICES, not probabilities: no calibration exists yet. Each factor is scored 0 (ok), 0.5 (attenzione)
  or 1 (rischio / forte) on a conventional starting threshold, and every factor has the SAME weight (an equal-weight
  checklist is the least arbitrary choice without data). The research module measures each factor against the
  real outcomes collected in the feature store; only validated changes may later replace these thresholds;
* a missing input is "non disponibile": it is excluded from the average and lowers ``coverage``; it is never
  scored as favourable. With coverage < 50% the index is reported as not determinable;
* opportunity can NEVER override risk: blocking findings (security, mayhem curve, failed sell simulation) exclude
  the token whatever its opportunity index.

Rules in ``enforce`` mode act on the portfolios. Rules in ``shadow`` mode only record what they WOULD have done;
the "x_safe" experiment applies them in a separate virtual portfolio so their effect can be measured out of
sample before anyone decides to promote them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from mci.domain import TokenSnapshot

INDEX_VERSION = 1
NOTE = "indice euristico 0-100 a pesi uguali, NON è una probabilità (non ancora calibrato sui dati)"


@dataclass
class Factor:
    name: str
    value: Any
    level: float | None  # 0 ok, 0.5 attenzione, 1 rischio/forte; None = non disponibile
    note: str


@dataclass
class IndexResult:
    value: float | None  # 0-100, None when coverage < 50%
    coverage: float
    factors: list[Factor] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)
    shadow_hits: list[str] = field(default_factory=list)
    version: int = INDEX_VERSION
    note: str = NOTE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _level(v: float | None, warn: float, bad: float, higher_is_worse: bool = True) -> float | None:
    if v is None:
        return None
    if higher_is_worse:
        return 1.0 if v >= bad else 0.5 if v >= warn else 0.0
    return 1.0 if v <= bad else 0.5 if v <= warn else 0.0


def _finish(factors: list[Factor]) -> tuple[float | None, float]:
    avail = [f.level for f in factors if f.level is not None]
    coverage = len(avail) / len(factors) if factors else 0.0
    if coverage < 0.5 or not avail:
        return None, round(coverage, 3)
    return round(sum(avail) / len(avail) * 100, 1), round(coverage, 3)


# ----------------------------------------------------------------------------- rules
@dataclass(frozen=True)
class Rule:
    code: str
    mode: str  # enforce | shadow
    description: str


RULES = {
    "ONCHAIN_SECURITY": Rule("ONCHAIN_SECURITY", "enforce", "rischio critico/alto nel contratto letto on-chain"),
    "MAYHEM_CURVE": Rule("MAYHEM_CURVE", "enforce", "curva 'mayhem' di pump.fun: prezzo mosso da un agente, non organico"),
    "SELL_SIM_FAILED": Rule("SELL_SIM_FAILED", "enforce", "la vendita simulata on-chain di un holder reale fallisce"),
    "HIGH_RISK_INDEX": Rule("HIGH_RISK_INDEX", "shadow", "indice di rischio >= 60"),
    "COORDINATED_SUPPLY": Rule("COORDINATED_SUPPLY", "shadow", "wallet coordinati/blocco 0 con >= 20% della supply"),
    "CREATOR_SOLD": Rule("CREATOR_SOLD", "shadow", "il creatore ha già venduto nei primi minuti"),
    "SERIAL_DEPLOYER": Rule("SERIAL_DEPLOYER", "shadow", "il creatore ha lanciato >= 3 token nelle ultime 24 h"),
}


def risk_index(snap: TokenSnapshot, f: dict[str, Any] | None = None, w: dict[str, Any] | None = None,
               h: dict[str, Any] | None = None) -> IndexResult:
    """Two factor sets: launches observed on the chain stream (early-trade facts available) and other tokens
    (market/holder data). Factors that do not apply to the token are not listed, so they do not lower coverage."""
    f = f if (f and f.get("complete")) else {}
    w = w if (w and (w.get("coverage") or 0) >= 0.7) else {}
    h = h or {}
    factors: list[Factor] = []
    serial = h.get("launches_24h") if h and h.get("observed_days", 0) >= 1 else None
    rug = h.get("rug_share") if h and (h.get("labeled") or 0) >= 3 else None
    cs = f.get("creator_sold") if f else None
    if f:
        top10 = f.get("top10_net_pct")
        coord = w.get("coordinated_pct") if w else f.get("same_slot_pct")
        factors += [
            Factor("concentrazione top 10", top10, _level(top10, 20, 35), "% della supply nei primi 10 holder"),
            Factor("supply a wallet coordinati / blocco 0", coord, _level(coord, 8, 20),
                   "cluster di finanziamento + finanziati dal creatore + acquisti nel blocco di creazione"
                   if w else "acquisti nel blocco di creazione (wallet non ancora analizzati)"),
            Factor("sniper nei primi 3 slot", f.get("sniper_pct"), _level(f.get("sniper_pct"), 3, 10),
                   "% della supply ancora in mano agli sniper"),
            Factor("il creatore ha venduto", cs, None if cs is None else (1.0 if cs else 0.0),
                   "vendite del creatore nella finestra osservata"),
            Factor("quota del creatore", f.get("creator_net_pct"), _level(f.get("creator_net_pct"), 5, 10),
                   "% della supply"),
            Factor("flipper (comprano e rivendono subito)", f.get("flipper_share"),
                   _level(f.get("flipper_share"), 0.3, 0.5), "quota dei compratori"),
            Factor("wallet nuovi tra i primi acquirenti", w.get("fresh_share") if w else None,
                   _level(w.get("fresh_share") if w else None, 0.4, 0.6), "wallet con meno di 3 giorni di storia"),
        ]
    else:
        coord = snap.early_buyer_cluster_pct if snap.early_buyer_cluster_pct is not None else snap.insider_cluster_pct
        factors += [
            Factor("concentrazione top 10", snap.top10_pct, _level(snap.top10_pct, 20, 35), "% della supply"),
            Factor("singolo holder più grande", snap.top1_pct, _level(snap.top1_pct, 5, 10), "% della supply"),
            Factor("insider / cluster", coord, _level(coord, 8, 20), "% della supply a wallet collegati"),
            Factor("quota del creatore", snap.dev_pct, _level(snap.dev_pct, 5, 10), "% della supply"),
            Factor("numero di holder", snap.holders_count, _level(snap.holders_count, 300, 100, higher_is_worse=False),
                   "pochi holder = mercato sottile"),
        ]
    factors.append(Factor("wash trading", snap.wash_score, _level(snap.wash_score, 0.4, 0.75), "0 pulito .. 1 manipolato"))
    if serial is not None or rug is not None or f:
        factors.append(Factor("lanci del creatore nelle ultime 24 h", serial, _level(serial, 2, 3),
                              "dal nostro storico dei lanci (serve almeno 1 giorno di raccolta)"))
        factors.append(Factor("rug precedenti del creatore", rug, _level(rug, 0.3, 0.6), "quota dei suoi token crollati"))
    if "onchain_security" in snap.sources:
        medium = [x for x in (snap.onchain_findings or []) if x.get("severity") == "medium"]
        factors.append(Factor("avvisi del contratto", len(medium), 0.0 if not medium else 0.5 if len(medium) == 1 else 1.0,
                              ", ".join(x.get("code", "") for x in medium) or "nessuno"))
    value, coverage = _finish(factors)
    res = IndexResult(value, coverage, factors)
    res.blocking = blocking_codes(snap)
    hits = []
    if value is not None and value >= 60:
        hits.append("HIGH_RISK_INDEX")
    if coord is not None and coord >= 20:
        hits.append("COORDINATED_SUPPLY")
    if cs:
        hits.append("CREATOR_SOLD")
    if serial is not None and serial >= 3:
        hits.append("SERIAL_DEPLOYER")
    res.shadow_hits = hits
    return res


def blocking_codes(snap: TokenSnapshot) -> list[str]:
    out = []
    if any(x.get("blocking") for x in (snap.onchain_findings or [])):
        out.append("ONCHAIN_SECURITY")
    if snap.bonding_curve and snap.mayhem is True:
        out.append("MAYHEM_CURVE")
    if snap.sell_sim_ok is False:
        out.append("SELL_SIM_FAILED")
    return out


def opportunity_index(snap: TokenSnapshot, f: dict[str, Any] | None = None,
                      w: dict[str, Any] | None = None) -> IndexResult:
    if (f and f.get("mayhem")) or (snap.bonding_curve and snap.mayhem):
        # agent-driven curve: buyer counts and pressure are not organic, an opportunity reading would be fiction
        return IndexResult(None, 0.0, [Factor("curva mayhem", True, None, "dinamica non organica: indice non calcolato")])
    f = f if (f and f.get("complete")) else {}
    w = w if (w and (w.get("coverage") or 0) >= 0.7) else {}
    factors: list[Factor] = []
    if f:  # bonding-curve token observed on the chain stream
        factors.append(Factor("acquirenti unici", f.get("unique_buyers"), _level(f.get("unique_buyers"), 15, 30), ""))
        factors.append(Factor("acquirenti indipendenti", w.get("independent_buyers") if w else None,
                              _level(w.get("independent_buyers") if w else None, 8, 15),
                              "non collegati da finanziamenti, non nel blocco 0"))
        factors.append(Factor("pressione d'acquisto", f.get("buy_pressure"), _level(f.get("buy_pressure"), 0.5, 0.6),
                              "SOL comprati / SOL scambiati"))
        factors.append(Factor("acquirenti nell'ultimo minuto", f.get("buyers_last_60s"),
                              _level(f.get("buyers_last_60s"), 2, 5), ""))
        factors.append(Factor("velocità della curva", f.get("progress_per_min"), _level(f.get("progress_per_min"), 0.5, 2),
                              "% della curva per minuto"))
        dd = f.get("drawdown_from_peak_pct")
        factors.append(Factor("distanza dal massimo", dd, _level(dd, 40, 20, higher_is_worse=False), "% sotto il picco"))
    else:  # DEX token: market data
        b5 = snap.buyers.get("m5")
        factors.append(Factor("acquirenti unici 5m", b5, _level(b5, 20, 60), ""))
        buys, sells = snap.buys.get("h1"), snap.sells.get("h1")
        ratio = buys / (buys + sells) if buys is not None and sells is not None and (buys + sells) else None
        factors.append(Factor("rapporto acquisti 1h", ratio, _level(ratio, 0.5, 0.58), "acquisti / transazioni"))
        vol, liq = snap.vol("h1"), snap.liquidity_usd
        turn = vol / liq if vol is not None and liq else None
        factors.append(Factor("volume 1h / liquidità", turn, _level(turn, 0.5, 1.5), ""))
        ch = snap.price_change_pct.get("h1")
        mom = None if ch is None else (1.0 if 10 <= ch <= 150 else 0.5 if 0 <= ch < 10 else 0.0)
        factors.append(Factor("momentum 1h", ch, mom, "+10..+150% forte, oltre = troppo esteso"))
    value, coverage = _finish(factors)
    return IndexResult(value, coverage, factors)
