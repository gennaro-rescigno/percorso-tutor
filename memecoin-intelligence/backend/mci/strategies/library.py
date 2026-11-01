"""Strategies A-E. Every threshold is a parameter so the backtester can test it.

Default timeframes: A=1m, B=5m, C=5m, D=15m, E=1h.
"""

from __future__ import annotations

from dataclasses import dataclass

from mci.strategies import indicators as ind
from mci.strategies.base import Decision, MarketContext, Strategy, StrategyParams


def _check(d: Decision, ok: bool, passed: str, failed: str) -> bool:
    (d.passed if ok else d.failed).append(passed if ok else failed)
    return ok


# =============================================================================
# A - EARLY ENTRY
# =============================================================================
@dataclass
class EarlyEntryParams(StrategyParams):
    min_score: float = 68.0
    min_age_min: float = 15.0
    max_age_min: float = 360.0
    min_liquidity_usd: float = 20_000.0
    min_vol_accel: float = 1.3
    min_buyer_growth: float = 1.1
    min_buyers_h1: int = 50
    buy_ratio_min: float = 0.52
    buy_ratio_max: float = 0.80
    min_change_h1: float = 5.0
    max_change_h1: float = 300.0
    max_wash: float = 0.5
    stop_lookback: int = 15


class EarlyEntry(Strategy):
    code = "A"
    name = "Early Entry"
    default_timeframe = "1m"
    params_cls = EarlyEntryParams
    params: EarlyEntryParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s, c = self.params, ctx.snapshot, ctx.candles
        d = Decision(None)
        if not self._gate_score(ctx, d):
            return d
        price = ctx.price
        if not price:
            d.failed.append("prezzo non disponibile")
            return d
        age = s.age_minutes
        if age is None:
            d.failed.append("età sconosciuta")
            return d
        if not _check(d, p.min_age_min <= age <= p.max_age_min, f"età {age:.0f} min nella finestra early",
                      f"età fuori finestra ({age:.0f} min)"):
            return d
        liq = s.liquidity_usd
        if not ctx.reduced:
            if liq is None:
                d.failed.append("liquidità sconosciuta")
                return d
            if not _check(d, liq >= p.min_liquidity_usd, f"liquidità {liq:,.0f} $", f"liquidità {liq:,.0f} $ insufficiente"):
                return d

        # volume acceleration: snapshot (5m vs 1h) or candles (last 5 bars vs last 60)
        accel = None
        vm5, vh1 = s.vol("m5"), s.vol("h1")
        if vm5 is not None and vh1:
            accel = vm5 * 12 / vh1
        elif len(c) >= 60:
            last5 = sum(x.volume for x in c[-5:])
            last60 = sum(x.volume for x in c[-60:])
            accel = (last5 * 12 / last60) if last60 > 0 else None
        if accel is None:
            d.failed.append("accelerazione del volume non calcolabile")
            return d
        if not _check(d, accel >= p.min_vol_accel, f"volume in accelerazione ({accel:.2f}x)",
                      f"accelerazione volume {accel:.2f}x < {p.min_vol_accel}"):
            return d

        ch1 = s.price_change_pct.get("h1")
        if ch1 is None and len(c) > 60:
            ch1 = (ind.pct_change(c, 60) or 0) * 100
        if ch1 is None:
            d.failed.append("variazione 1h non disponibile")
            return d
        if not _check(d, p.min_change_h1 <= ch1 <= p.max_change_h1, f"prezzo {ch1:+.0f}% in 1h",
                      f"variazione 1h {ch1:+.0f}% fuori range [{p.min_change_h1:.0f}, {p.max_change_h1:.0f}]"):
            return d

        b, se = s.buys.get("h1"), s.sells.get("h1")
        if b is not None and se is not None and b + se > 0:
            r = b / (b + se)
            if not _check(d, p.buy_ratio_min <= r <= p.buy_ratio_max, f"pressione in acquisto sana ({r:.2f})",
                          f"buy ratio {r:.2f} fuori range"):
                return d
        elif not ctx.reduced:
            d.failed.append("rapporto buy/sell non disponibile")
            return d

        by5, by1 = s.buyers.get("m5"), s.buyers.get("h1")
        if by1 is not None:
            if not _check(d, by1 >= p.min_buyers_h1, f"{by1} compratori unici in 1h", f"solo {by1} compratori unici in 1h"):
                return d
            if by5 is not None:
                g = by5 * 12 / by1
                if not _check(d, g >= p.min_buyer_growth, f"compratori in aumento ({g:.2f}x)", f"compratori non in aumento ({g:.2f}x)"):
                    return d
        elif not ctx.reduced:
            d.failed.append("compratori unici non disponibili")
            return d

        if s.wash_score is not None and not _check(d, s.wash_score <= p.max_wash, f"volume pulito (wash {s.wash_score:.2f})",
                                                   f"wash score {s.wash_score:.2f} troppo alto"):
            return d

        low = ind.lowest_low(c, min(p.stop_lookback, len(c))) if c else None
        stop = (low * 0.97) if low else price * (1 - 0.2)
        return Decision(self._make_signal(ctx, stop, d, {"vol_accel": accel, "change_h1": ch1, "age_min": age}),
                        d.failed, d.passed)


# =============================================================================
# B - MOMENTUM / BREAKOUT
# =============================================================================
@dataclass
class MomentumParams(StrategyParams):
    min_score: float = 65.0
    min_age_min: float = 180.0
    breakout_lookback: int = 48
    vol_mult: float = 2.0
    vol_lookback: int = 48
    ema_fast: int = 20
    ema_slow: int = 50
    max_extension: float = 0.30
    min_liquidity_usd: float = 30_000.0
    max_change_h1: float = 150.0
    atr_mult: float = 2.5


class Momentum(Strategy):
    code = "B"
    name = "Momentum"
    default_timeframe = "5m"
    params_cls = MomentumParams
    params: MomentumParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s, c = self.params, ctx.snapshot, ctx.candles
        d = Decision(None)
        if not self._gate_score(ctx, d):
            return d
        need = max(p.breakout_lookback, p.ema_slow, p.vol_lookback) + 2
        if len(c) < need:
            d.failed.append(f"storico insufficiente ({len(c)}/{need} candele)")
            return d
        age = s.age_minutes
        if age is not None and not _check(d, age >= p.min_age_min, f"token avviato ({age / 60:.1f} h)", f"token troppo giovane per momentum ({age:.0f} min)"):
            return d
        if not ctx.reduced and s.liquidity_usd is not None and not _check(
            d, s.liquidity_usd >= p.min_liquidity_usd, f"liquidità {s.liquidity_usd:,.0f} $", "liquidità insufficiente"
        ):
            return d
        last = c[-1]
        hh = ind.highest_high(c, p.breakout_lookback)
        if not _check(d, hh is not None and last.close > hh, f"breakout sopra il massimo di {p.breakout_lookback} candele",
                      "nessun breakout"):
            return d
        av = ind.avg_volume(c, p.vol_lookback)
        if not _check(d, bool(av) and last.volume >= p.vol_mult * av, f"volume del breakout {last.volume / av:.1f}x la media" if av else "",
                      "volume del breakout insufficiente"):
            return d
        closes = [x.close for x in c]
        ef, es = ind.ema(closes, p.ema_fast)[-1], ind.ema(closes, p.ema_slow)[-1]
        if not _check(d, ef > es, "trend rialzista (EMA veloce > lenta)", "trend non rialzista"):
            return d
        ext = last.close / ef - 1
        if not _check(d, ext <= p.max_extension, f"estensione contenuta ({ext:.0%} sopra EMA{p.ema_fast})",
                      f"prezzo troppo esteso ({ext:.0%} sopra EMA): non si insegue il pump"):
            return d
        ch1 = s.price_change_pct.get("h1")
        if ch1 is not None and not _check(d, ch1 <= p.max_change_h1, f"variazione 1h {ch1:+.0f}%", f"variazione 1h {ch1:+.0f}% eccessiva"):
            return d
        a = ind.atr(c, 14) or (last.close * 0.1)
        stop = max(hh * 0.92, last.close - p.atr_mult * a)
        return Decision(self._make_signal(ctx, stop, d, {"breakout_level": hh, "extension": ext, "atr": a}), d.failed, d.passed)


# =============================================================================
# C - PULLBACK
# =============================================================================
@dataclass
class PullbackParams(StrategyParams):
    min_score: float = 65.0
    impulse_lookback: int = 144
    min_impulse: float = 0.8  # +80% from base to high
    retrace_min: float = 0.30
    retrace_max: float = 0.62
    max_vol_ratio: float = 0.7  # pullback volume / impulse volume
    ema_reclaim: int = 9
    min_liquidity_usd: float = 25_000.0


class Pullback(Strategy):
    code = "C"
    name = "Pullback"
    default_timeframe = "5m"
    params_cls = PullbackParams
    params: PullbackParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s, c = self.params, ctx.snapshot, ctx.candles
        d = Decision(None)
        if not self._gate_score(ctx, d):
            return d
        if len(c) < min(p.impulse_lookback, 60):
            d.failed.append("storico insufficiente per il pullback")
            return d
        if not ctx.reduced and s.liquidity_usd is not None and not _check(
            d, s.liquidity_usd >= p.min_liquidity_usd, f"liquidità {s.liquidity_usd:,.0f} $", "liquidità insufficiente"
        ):
            return d
        win = c[-p.impulse_lookback:]
        hi_idx = max(range(len(win)), key=lambda i: win[i].high)
        if hi_idx >= len(win) - 3 or hi_idx < 3:
            d.failed.append("nessun massimo di impulso utilizzabile")
            return d
        base_idx = min(range(0, hi_idx), key=lambda i: win[i].low)
        base, high = win[base_idx].low, win[hi_idx].high
        impulse = high / base - 1 if base > 0 else 0
        if not _check(d, impulse >= p.min_impulse, f"impulso precedente +{impulse:.0%}", f"impulso solo +{impulse:.0%}"):
            return d
        after = win[hi_idx + 1:]
        pb_low = min(x.low for x in after)
        last = c[-1]
        retr = (high - pb_low) / (high - base) if high > base else 1
        if not _check(d, p.retrace_min <= retr <= p.retrace_max, f"ritracciamento {retr:.0%} (struttura intatta)",
                      f"ritracciamento {retr:.0%} fuori range"):
            return d
        imp_vol = sum(x.volume for x in win[base_idx:hi_idx + 1]) / max(1, hi_idx + 1 - base_idx)
        pb_vol = sum(x.volume for x in after) / max(1, len(after))
        vr = pb_vol / imp_vol if imp_vol > 0 else 9
        if not _check(d, vr <= p.max_vol_ratio, f"volume in calo durante la correzione ({vr:.2f}x)",
                      f"volume della correzione troppo alto ({vr:.2f}x): possibile distribuzione"):
            return d
        closes = [x.close for x in c]
        e = ind.ema(closes, p.ema_reclaim)[-1]
        prev = c[-2]
        av20 = ind.avg_volume(c, 20) or 0
        ok = last.close > e and last.close > prev.high and last.volume > av20
        if not _check(d, ok, "segnale di ripresa (recupero EMA e massimo precedente con volume)", "nessun segnale di ripresa"):
            return d
        stop = pb_low * 0.97
        return Decision(self._make_signal(ctx, stop, d, {"impulse": impulse, "retracement": retr, "vol_ratio": vr}), d.failed, d.passed)


# =============================================================================
# D - ACCUMULATION
# =============================================================================
@dataclass
class AccumulationParams(StrategyParams):
    min_score: float = 65.0
    range_bars: int = 32
    max_range: float = 0.30
    recent_bars: int = 8
    vol_rise_ratio: float = 1.3
    min_holder_growth: float = 0.02
    min_age_min: float = 360.0
    breakout_vol_mult: float = 1.5


class Accumulation(Strategy):
    code = "D"
    name = "Accumulazione"
    default_timeframe = "15m"
    params_cls = AccumulationParams
    params: AccumulationParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s, c = self.params, ctx.snapshot, ctx.candles
        d = Decision(None)
        if not self._gate_score(ctx, d):
            return d
        if len(c) < p.range_bars + p.recent_bars + 2:
            d.failed.append("storico insufficiente per l'accumulazione")
            return d
        age = s.age_minutes
        if age is not None and not _check(d, age >= p.min_age_min, "token con storico sufficiente", "token troppo giovane"):
            return d
        rng = c[-(p.range_bars + 1):-1]
        hi, lo = max(x.high for x in rng), min(x.low for x in rng)
        width = hi / lo - 1 if lo > 0 else 9
        if not _check(d, width <= p.max_range, f"prezzo in range stretto ({width:.0%})", f"range troppo ampio ({width:.0%})"):
            return d
        recent = rng[-p.recent_bars:]
        older = rng[:-p.recent_bars]
        rv = sum(x.volume for x in recent) / len(recent)
        ov = sum(x.volume for x in older) / max(1, len(older))
        vr = rv / ov if ov > 0 else 0
        if not _check(d, vr >= p.vol_rise_ratio, f"volume crescente a prezzo stabile ({vr:.2f}x)", f"volume non in crescita ({vr:.2f}x)"):
            return d
        # holder / liquidity growth from point-in-time history (if recorded)
        if ctx.history:
            first = next((h for h in ctx.history if h.holders_count), None)
            if first and s.holders_count:
                g = s.holders_count / first.holders_count - 1
                if not _check(d, g >= p.min_holder_growth, f"holder in crescita ({g:+.1%})", f"holder non in crescita ({g:+.1%})"):
                    return d
            firstl = next((h for h in ctx.history if h.liquidity_usd), None)
            if firstl and s.liquidity_usd and not _check(
                d, s.liquidity_usd >= firstl.liquidity_usd, "liquidità in aumento", "liquidità in calo"
            ):
                return d
        elif not ctx.reduced:
            d.failed.append("storico point-in-time di holder/liquidità non ancora disponibile")
            return d
        b, se = s.buys.get("h6"), s.sells.get("h6")
        if b is not None and se is not None and b + se > 0 and not _check(
            d, b / (b + se) >= 0.52, f"prevalenza di acquisti ({b / (b + se):.2f})", "nessuna prevalenza di acquisti"
        ):
            return d
        last = c[-1]
        if not _check(d, last.close > hi and last.volume >= p.breakout_vol_mult * ov,
                      "uscita dal range con volume", "nessuna uscita dal range con volume"):
            return d
        stop = lo * 0.97
        return Decision(self._make_signal(ctx, stop, d, {"range_width": width, "vol_ratio": vr}), d.failed, d.passed)


# =============================================================================
# E - REVIVAL
# =============================================================================
@dataclass
class RevivalParams(StrategyParams):
    min_score: float = 62.0
    min_age_days: float = 7.0
    dormant_bars: int = 144
    recent_bars: int = 24
    vol_revival_mult: float = 3.0
    min_drawdown_from_ath: float = 0.70
    breakout_lookback: int = 72
    min_liquidity_usd: float = 20_000.0


class Revival(Strategy):
    code = "E"
    name = "Revival"
    default_timeframe = "1h"
    params_cls = RevivalParams
    params: RevivalParams

    def evaluate(self, ctx: MarketContext) -> Decision:
        p, s, c = self.params, ctx.snapshot, ctx.candles
        d = Decision(None)
        if not self._gate_score(ctx, d):
            return d
        need = p.dormant_bars + p.recent_bars
        if len(c) < need:
            d.failed.append(f"storico insufficiente ({len(c)}/{need} candele orarie)")
            return d
        age = s.age_minutes
        if age is not None and not _check(d, age >= p.min_age_days * 1440, f"token di {age / 1440:.0f} giorni", "token non abbastanza vecchio"):
            return d
        if not ctx.reduced and s.liquidity_usd is not None and not _check(
            d, s.liquidity_usd >= p.min_liquidity_usd, f"liquidità {s.liquidity_usd:,.0f} $", "liquidità insufficiente"
        ):
            return d
        dormant = c[-need:-p.recent_bars]
        recent = c[-p.recent_bars:]
        dv = sum(x.volume for x in dormant) / len(dormant)
        rv = sum(x.volume for x in recent) / len(recent)
        mult = rv / dv if dv > 0 else (9.0 if rv > 0 else 0.0)
        if not _check(d, mult >= p.vol_revival_mult, f"volume tornato a {mult:.1f}x la fase dormiente", f"volume solo {mult:.1f}x"):
            return d
        ath = max(x.high for x in c)
        last = c[-1]
        dd = 1 - last.close / ath if ath > 0 else 0
        if not _check(d, dd >= p.min_drawdown_from_ath, f"lontano dai massimi ({dd:.0%} sotto ATH): spazio di recupero",
                      f"non è un revival (solo {dd:.0%} sotto ATH)"):
            return d
        hh = ind.highest_high(c, p.breakout_lookback)
        if not _check(d, hh is not None and last.close > hh, f"rottura del massimo di {p.breakout_lookback}h", "nessuna rottura dei massimi recenti"):
            return d
        if s.social_metrics.get("reddit") is not None:
            d.passed.append("menzioni social disponibili")
        low = ind.lowest_low(c, 24) or last.close * 0.8
        stop = low * 0.95
        return Decision(self._make_signal(ctx, stop, d, {"vol_mult": mult, "drawdown_from_ath": dd}), d.failed, d.passed)


STRATEGIES: dict[str, type[Strategy]] = {
    "A": EarlyEntry,
    "B": Momentum,
    "C": Pullback,
    "D": Accumulation,
    "E": Revival,
}


def build_strategy(code: str, params: dict | None = None) -> Strategy:
    cls = STRATEGIES[code.upper()]
    return cls(params)
