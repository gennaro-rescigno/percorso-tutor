"""O - Organic curve momentum (EXPERIMENTAL, shadow only: runs in the "x_curve" virtual portfolio).

Hypothesis (pre-registered, parameters frozen at version 1 so that the out-of-sample test is honest):
a pump.fun launch that, 2-15 minutes after creation, shows broad and independent demand (many unique buyers,
buying pressure, buyers still arriving in the last minute), no early dumping by the creator and limited
sniper/top-holder concentration, continues upward often enough to beat the costs.

It is NOT used by the main portfolio. It can only be considered for promotion after the promotion gate
(enough out-of-sample trades, confidence interval above zero, beats the Laboratorio baseline) and the owner's
explicit approval.
"""

from __future__ import annotations

from dataclasses import dataclass

from mci.strategies.base import Decision, MarketContext, Strategy, StrategyParams


@dataclass
class OrganicCurveParams(StrategyParams):
    min_score: float = 0.0  # the classic score is not designed for 5-minute-old tokens: own conditions below
    min_age_s: float = 120
    max_age_s: float = 900
    min_unique_buyers: int = 25
    min_buyers_last_60s: int = 4
    min_buy_pressure: float = 0.58
    min_progress_pct: float = 10
    max_progress_pct: float = 80
    max_drawdown_from_peak_pct: float = 25
    max_top10_net_pct: float = 30
    max_sniper_pct: float = 10
    max_risk_index: float = 50
    stop_pct: float = 0.25


def _ok(d: Decision, cond: bool, good: str, bad: str) -> bool:
    (d.passed if cond else d.failed).append(good if cond else bad)
    return cond


class OrganicCurve(Strategy):
    code = "O"
    name = "Curva organica (sperimentale)"
    default_timeframe = "1m"
    params_cls = OrganicCurveParams
    params: OrganicCurveParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s = self.params, ctx.snapshot
        d = Decision(None)
        if ctx.score is None or ctx.score.excluded:
            d.failed.append("token escluso dai filtri di sicurezza")
            return d
        f = (s.onchain or {}).get("curve") or {}
        if not f.get("complete"):
            d.failed.append("dati della curva incompleti (stream non continuo)")
            return d
        price = s.price_native or ctx.price
        if not price:
            d.failed.append("prezzo non disponibile")
            return d
        checks = [
            (p.min_age_s <= f["age_s"] <= p.max_age_s, f"età {f['age_s'] / 60:.1f} min", "età fuori finestra"),
            (f["unique_buyers"] >= p.min_unique_buyers, f"{f['unique_buyers']} acquirenti unici", "pochi acquirenti unici"),
            (f["buyers_last_60s"] >= p.min_buyers_last_60s, f"{f['buyers_last_60s']} acquirenti nell'ultimo minuto",
             "domanda non più attiva"),
            ((f.get("buy_pressure") or 0) >= p.min_buy_pressure, f"pressione d'acquisto {f.get('buy_pressure')}",
             "pressione d'acquisto debole"),
            (p.min_progress_pct <= (f.get("progress_pct") or 0) <= p.max_progress_pct,
             f"curva al {f.get('progress_pct')}%", "progresso della curva fuori range"),
            ((f.get("drawdown_from_peak_pct") or 0) <= p.max_drawdown_from_peak_pct, "vicino ai massimi",
             "troppo sotto il massimo"),
            (f.get("creator_sold") is False, "il creatore non ha venduto", "il creatore ha venduto (o dato mancante)"),
            ((f.get("top10_net_pct") if f.get("top10_net_pct") is not None else 100) <= p.max_top10_net_pct,
             f"top 10 {f.get('top10_net_pct')}%", "concentrazione top 10 troppo alta"),
            ((f.get("sniper_pct") if f.get("sniper_pct") is not None else 100) <= p.max_sniper_pct,
             f"sniper {f.get('sniper_pct')}%", "troppa supply agli sniper"),
        ]
        for cond, good, bad in checks:
            if not _ok(d, bool(cond), good, bad):
                return d
        risk = ((s.onchain or {}).get("risk") or {}).get("value")
        if risk is not None and not _ok(d, risk <= p.max_risk_index, f"indice di rischio {risk:.0f}",
                                        f"indice di rischio {risk:.0f} troppo alto"):
            return d
        stop = price * (1 - p.stop_pct)
        return Decision(self._make_signal(ctx, stop, d, {k: f.get(k) for k in (
            "age_s", "unique_buyers", "buyers_last_60s", "buy_pressure", "progress_pct", "top10_net_pct", "sniper_pct")}),
            d.failed, d.passed)

    @staticmethod
    def precheck(f: dict) -> bool:
        """Cheap pre-filter on stream features before any RPC call is spent on the token."""
        p = OrganicCurveParams()
        return bool(f.get("complete") and not f.get("mayhem") and p.min_age_s <= f.get("age_s", 0) <= p.max_age_s
                    and f.get("unique_buyers", 0) >= p.min_unique_buyers
                    and f.get("buyers_last_60s", 0) >= p.min_buyers_last_60s
                    and (f.get("buy_pressure") or 0) >= p.min_buy_pressure)
