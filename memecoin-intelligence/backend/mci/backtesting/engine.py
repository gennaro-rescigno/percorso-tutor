"""Event-driven, portfolio-level backtest engine.

Point-in-time guarantees
------------------------
* All tokens are replayed on ONE global clock (bars sorted by time), sharing one
  capital account, so position limits and compounding behave as in live trading.
* A decision taken on bar *i* only sees candles ``[.., i]`` and snapshots observed
  before the bar close; the order is filled on bar *i+1* at its OPEN (+latency slip).
* A token cannot be traded before ``first_seen_at`` (when the scanner discovered it).

Execution realism
-----------------
* DEX fee per venue, network fee per transaction (also on failed transactions),
  ATA rent (refunded on full exit, lost on dead tokens).
* Constant-product price impact on the quote reserve estimated point-in-time
  (x_t = x_0 * sqrt(p_t / p_0)), with an extra haircut after rug-like crashes.
* Random transaction failures (seeded), stop gaps, pessimistic intrabar ordering.
* Positions on tokens whose data stops (dead/illiquid) are closed at
  ``dead_token_recovery`` x last price (default 0 = total loss).
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from mci.backtesting.data import Dataset, TokenSeries
from mci.backtesting.metrics import Metrics, TradeRecord, compute_metrics
from mci.domain import Candle, Signal, TokenSnapshot
from mci.execution.costs import CostModel, amm_buy, amm_sell, dex_fee
from mci.risk_management.exits import EXIT_POLICIES, ExitPolicy, PositionState, evaluate_bar, initial_stop
from mci.risk_management.manager import PortfolioState, RiskManager
from mci.risk_management.profiles import get_profile
from mci.scoring.scorer import score_token
from mci.strategies import indicators as ind
from mci.strategies.base import MarketContext
from mci.strategies.library import build_strategy


@dataclass
class BacktestConfig:
    strategy_codes: list[str]
    strategy_params: dict[str, dict[str, Any]] = field(default_factory=dict)
    profile: str = "moderate"
    profile_overrides: dict[str, Any] = field(default_factory=dict)
    exit_policy: str = "ladder_trailing"
    exit_overrides: dict[str, Any] = field(default_factory=dict)
    initial_capital_sol: float = 2.0
    entry_start_ts: int | None = None
    entry_end_ts: int | None = None
    priority_fee_sol: float = 0.0001
    jito_tip_sol: float = 0.0
    p_fail_entry: float = 0.05
    p_fail_exit: float = 0.03
    latency_slippage_pct: float = 0.005
    rug_drop_threshold: float = 0.80
    rug_reserve_haircut: float = 0.15
    dead_token_recovery: float = 0.0
    dead_gap_bars: int = 60
    detection_delay_s: int = 20
    allow_reduced: bool = True
    max_lookback_bars: int = 400
    warmup_bars: int = 20
    equity_sample_s: int = 3600
    seed: int = 42

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: Metrics
    trades: list[TradeRecord]
    equity_curve: list[tuple[datetime, float]]
    signals: int
    rejections: dict[str, int]
    warnings: list[str]
    data_info: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "metrics": self.metrics.to_dict(),
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": [[t.isoformat(), v] for t, v in self.equity_curve],
            "signals": self.signals,
            "rejections": self.rejections,
            "warnings": self.warnings,
            "data_info": self.data_info,
        }


def _dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@dataclass
class _SeriesState:
    series: TokenSeries
    snap_idx: int = 0
    rugged: bool = False
    last_close: float = 0.0
    last_ts: int = 0
    pending_entry: tuple[Signal, float, float] | None = None  # (signal, size_sol, atr)
    position: PositionState | None = None
    trade_meta: dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.cfg = config
        self.profile = get_profile(config.profile).with_overrides(**config.profile_overrides) if config.profile_overrides else get_profile(config.profile)
        base_policy = EXIT_POLICIES[config.exit_policy]
        self.policy = ExitPolicy(**{**base_policy.to_dict(), **config.exit_overrides}) if config.exit_overrides else base_policy
        if isinstance(self.policy.take_profits, list):
            self.policy.take_profits = tuple(tuple(x) for x in self.policy.take_profits)
        self.costs = CostModel(priority_fee_sol=config.priority_fee_sol, jito_tip_sol=config.jito_tip_sol)
        self.risk = RiskManager(self.profile, self.costs)
        self.strategies = [build_strategy(c, config.strategy_params.get(c)) for c in config.strategy_codes]
        self.rng = random.Random(config.seed)

    # ------------------------------------------------------------------ helpers
    def _reserve(self, st: _SeriesState, price: float) -> float | None:
        s = st.series
        if not s.reserve_sol0 or not s.candles:
            return None
        p0 = s.candles[0].open
        if p0 <= 0 or price <= 0:
            return None
        r = s.reserve_sol0 * (price / p0) ** 0.5
        if st.rugged:
            r *= self.cfg.rug_reserve_haircut
        return r

    def _snapshot(self, st: _SeriesState, window: list[Candle], close_ts: int) -> tuple[TokenSnapshot, bool]:
        s = st.series
        reduced = True
        base: TokenSnapshot | None = None
        snaps = s.snapshots
        while st.snap_idx < len(snaps) and snaps[st.snap_idx].observed_at.timestamp() <= close_ts:
            st.snap_idx += 1
        if st.snap_idx > 0:
            base = snaps[st.snap_idx - 1]
            reduced = False
        now = _dt(close_ts)
        snap = TokenSnapshot(
            chain="solana", token_address=s.token, observed_at=now, symbol=s.symbol,
            pair_address=s.pool, dex_id=s.dex_id, created_at=s.created_at,
        )
        last = window[-1]
        snap.price_native = last.close
        vols: dict[str, float] = {}
        for w, minutes in (("m5", 5), ("m15", 15), ("h1", 60), ("h6", 360), ("h24", 1440)):
            cut = close_ts - minutes * 60
            vols[w] = sum(c.volume for c in window if c.ts + s.timeframe_s > cut)
        snap.volume_usd = vols
        for w, minutes in (("m5", 5), ("h1", 60), ("h6", 360), ("h24", 1440)):
            bars = max(1, minutes * 60 // s.timeframe_s)
            ch = ind.pct_change(window, bars)
            snap.price_change_pct[w] = ch * 100 if ch is not None else None
        reserve = self._reserve(st, last.close)
        if reserve is not None:
            snap.liquidity_quote = reserve
            if s.sol_usd:
                snap.liquidity_usd = 2 * reserve * s.sol_usd
        if base is not None:
            # point-in-time recorded features fill everything the candles cannot provide
            snap.merge(base)
        return snap, reduced

    def _equity(self, states: dict[str, _SeriesState], st: PortfolioState) -> float:
        val = 0.0
        for ss in states.values():
            if ss.position and ss.position.qty > 0:
                val += ss.position.qty * ss.last_close
                st.exposure[ss.series.token] = ss.position.qty * ss.last_close
        return st.cash + val

    # ------------------------------------------------------------------ execution
    def _execute_entry(self, ss: _SeriesState, bar: Candle, port: PortfolioState, counters: Counter,
                       warnings: list[str]) -> None:
        signal, size, atr_v = ss.pending_entry  # type: ignore[misc]
        ss.pending_entry = None
        s = ss.series
        if self.rng.random() < self.cfg.p_fail_entry:
            port.cash -= self.costs.network_fee_sol
            counters["ordine di acquisto fallito (tx fallita simulata)"] += 1
            self._failed += 1
            return
        size = min(size, port.cash - 2 * self.costs.network_fee_sol - self.costs.ata_rent_sol)
        if size < self.profile.min_position_sol:
            counters["cassa insufficiente al momento dell'esecuzione"] += 1
            return
        mid = bar.open * (1 + self.cfg.latency_slippage_pct)
        reserve = self._reserve(ss, bar.open)
        if not reserve:
            counters["riserva del pool sconosciuta"] += 1
            return
        mc_usd = None
        fee = dex_fee(s.dex_id, mc_usd)
        f = amm_buy(size, reserve, mid, fee)
        if f.out_amount <= 0:
            return
        network = self.costs.network_fee_sol
        rent = self.costs.ata_rent_sol
        total_cost = size + network + rent
        port.cash -= total_cost
        entry_price = size / f.out_amount
        stop = initial_stop(self.policy, entry_price, signal.stop_price * (entry_price / signal.reference_price), atr_v)
        window = s.candles[max(0, self._bar_idx[s.token] - 20): self._bar_idx[s.token]]
        vref = (sum(c.volume for c in window) / len(window)) if window else None
        ss.position = PositionState(
            token=s.token, strategy=signal.strategy, entry_time=_dt(bar.ts), entry_price=entry_price,
            qty_initial=f.out_amount, qty=f.out_amount, cost_sol=total_cost, stop_price=stop, initial_stop=stop,
            high_water=entry_price, entry_volume_ref=vref, entry_reserve_sol=reserve,
            fees_sol=f.fee_paid + network, slippage_sol=max(0.0, size - f.fee_paid - f.out_amount * bar.open),
        )
        ss.trade_meta = {"score": signal.score, "reduced": signal.reduced_features, "mfe": entry_price, "mae": entry_price,
                         "reasons": [], "exit_value_x_qty": 0.0, "exit_qty": 0.0}
        self.risk.on_entry(port, s.token, size)
        self._capital_used = max(self._capital_used, port.open_exposure)

    def _execute_exit(self, ss: _SeriesState, qty: float, price_hint: float, reason: str, now: datetime,
                      port: PortfolioState, *, dead: bool = False) -> bool:
        pos = ss.position
        assert pos is not None
        s = ss.series
        if not dead and self.rng.random() < self.cfg.p_fail_exit:
            port.cash -= self.costs.network_fee_sol
            pos.fees_sol += self.costs.network_fee_sol
            pos.cost_sol += self.costs.network_fee_sol
            self._failed += 1
            return False
        qty = min(qty, pos.qty)
        closing = qty >= pos.qty - 1e-12
        if dead:
            proceeds = qty * price_hint * self.cfg.dead_token_recovery
            fee_paid = 0.0
            slip = qty * price_hint - proceeds
            network = self.costs.network_fee_sol if proceeds > 0 else 0.0
            rent_refund = 0.0
        else:
            mid = price_hint * (1 - self.cfg.latency_slippage_pct)
            reserve = self._reserve(ss, price_hint) or 0.0
            fee = dex_fee(s.dex_id)
            f = amm_sell(qty, reserve, mid, fee)
            proceeds, fee_paid = f.out_amount, f.fee_paid
            slip = max(0.0, qty * price_hint - proceeds - fee_paid)
            network = self.costs.network_fee_sol
            rent_refund = self.costs.ata_rent_sol if closing else 0.0
        net = proceeds - network + rent_refund
        port.cash += net
        pos.qty -= qty
        pos.realized_sol += net
        pos.fees_sol += fee_paid + network
        pos.slippage_sol += slip
        m = ss.trade_meta
        m["reasons"].append(reason)
        m["exit_value_x_qty"] += (proceeds / qty if qty > 0 else 0.0) * qty
        m["exit_qty"] += qty
        if closing or pos.qty <= 1e-12:
            pnl = pos.realized_sol - pos.cost_sol
            self.trades.append(
                TradeRecord(
                    token=s.token, symbol=s.symbol, strategy=pos.strategy, entry_time=pos.entry_time, exit_time=now,
                    entry_price=pos.entry_price,
                    exit_price=(m["exit_value_x_qty"] / m["exit_qty"]) if m["exit_qty"] else 0.0,
                    qty=pos.qty_initial, cost_sol=pos.cost_sol, proceeds_sol=pos.realized_sol, pnl_sol=pnl,
                    return_pct=pnl / pos.cost_sol if pos.cost_sol else 0.0, fees_sol=pos.fees_sol,
                    slippage_sol=pos.slippage_sol, exit_reasons=list(m["reasons"]),
                    mfe_pct=m["mfe"] / pos.entry_price - 1, mae_pct=m["mae"] / pos.entry_price - 1,
                    score=m["score"], reduced_features=m["reduced"], dead_token=dead,
                )
            )
            self.risk.on_exit(port, s.token, pnl, now, closed=True)
            ss.position = None
        else:
            port.exposure[s.token] = pos.qty * ss.last_close
        return True

    # ------------------------------------------------------------------ main loop
    def run(self, ds: Dataset) -> BacktestResult:
        cfg = self.cfg
        warnings: list[str] = []
        counters: Counter = Counter()
        self.trades: list[TradeRecord] = []
        self._failed = 0
        self._capital_used = 0.0
        self._bar_idx: dict[str, int] = {}
        if not ds.info.survivorship_free:
            warnings.append("universo NON privo di survivorship bias: risultati probabilmente ottimistici")
        if not ds.info.point_in_time_features:
            warnings.append("feature point-in-time non disponibili: modalità ridotta (solo OHLCV)")
            if not cfg.allow_reduced:
                raise ValueError("dataset senza feature point-in-time e allow_reduced=False")

        states: dict[str, _SeriesState] = {}
        events: list[tuple[int, int, int]] = []
        series_list = [s for s in ds.series if s.candles]
        for k, s in enumerate(series_list):
            if not s.reserve_sol0:
                counters["token esclusi: liquidità iniziale sconosciuta"] += 1
                continue
            states[s.token] = _SeriesState(series=s)
            events.extend((c.ts, k, i) for i, c in enumerate(s.candles))
        events.sort()
        if not events:
            warnings.append("nessun dato utilizzabile")
        dataset_end = max((s.end_ts for s in series_list), default=0)

        port = PortfolioState(equity=cfg.initial_capital_sol, cash=cfg.initial_capital_sol, peak_equity=cfg.initial_capital_sol)
        curve: list[tuple[datetime, float]] = []
        next_sample = events[0][0] if events else 0
        n_signals = 0

        for ts, k, i in events:
            s = series_list[k]
            ss = states.get(s.token)
            if ss is None:
                continue
            bar = s.candles[i]
            now = _dt(ts)
            self._bar_idx[s.token] = i
            prev_close = ss.last_close or bar.open
            crash_bar = prev_close > 0 and bar.low < prev_close * (1 - cfg.rug_drop_threshold)
            if crash_bar:
                ss.rugged = True
            ss.last_close = bar.close
            ss.last_ts = ts

            # 1) pending entry fills at this bar's open
            if ss.pending_entry is not None:
                if ss.position is None:
                    self._execute_entry(ss, bar, port, counters, warnings)
                else:
                    ss.pending_entry = None

            # 2) exits on this bar
            pos = ss.position
            if pos is not None:
                ss.trade_meta["mfe"] = max(ss.trade_meta["mfe"], bar.high)
                ss.trade_meta["mae"] = min(ss.trade_meta["mae"], bar.low)
                recent = s.candles[max(0, i - 4): i + 1]
                vavg = sum(c.volume for c in recent) / len(recent)
                actions = evaluate_bar(
                    pos, self.policy, now=now + timedelta(seconds=s.timeframe_s), open_=bar.open, high=bar.high,
                    low=bar.low, close=bar.close, bar_volume_avg=vavg, reserve_sol=self._reserve(ss, bar.close),
                )
                for a in actions:
                    if ss.position is None:
                        break
                    hint = a.price_hint
                    if crash_bar and a.reason in ("STOP_LOSS", "TRAILING_STOP", "BREAKEVEN_STOP", "STOP_GAP"):
                        # a rug happens in one transaction: nobody gets filled at the stop level
                        hint = min(hint, bar.low)
                    self._execute_exit(ss, a.qty, hint, a.reason, now + timedelta(seconds=s.timeframe_s), port)
                # dead token: last bar of the series well before the dataset end
                if ss.position is not None and i == len(s.candles) - 1:
                    if s.end_ts < dataset_end - cfg.dead_gap_bars * s.timeframe_s:
                        self._execute_exit(ss, ss.position.qty, bar.close, "DEAD_TOKEN", now, port, dead=True)
                        counters["posizioni chiuse su token morti/illiquidi"] += 1
                    else:
                        self._execute_exit(ss, ss.position.qty, bar.close, "END_OF_DATA", now, port)

            # 3) mark to market & breakers
            equity = self._equity(states, port)
            for alert in self.risk.update_equity(port, equity, port.cash, now):
                warnings.append(f"{now:%Y-%m-%d %H:%M}: {alert}")
            if ts >= next_sample:
                curve.append((now, equity))
                next_sample = ts + cfg.equity_sample_s

            # 4) signal evaluation at bar close
            if ss.position is not None or ss.pending_entry is not None or i == len(s.candles) - 1:
                continue
            close_ts = ts + s.timeframe_s
            if cfg.entry_start_ts and close_ts < cfg.entry_start_ts:
                continue
            if cfg.entry_end_ts and close_ts >= cfg.entry_end_ts:
                continue
            if s.first_seen_at and close_ts < s.first_seen_at.timestamp() + cfg.detection_delay_s:
                continue
            if i + 1 < cfg.warmup_bars:
                continue
            window = s.candles[max(0, i + 1 - cfg.max_lookback_bars): i + 1]
            snap, reduced = self._snapshot(ss, window, close_ts)
            if reduced and not cfg.allow_reduced:
                continue
            score = None if reduced else score_token(snap, window, for_trading=True)
            ctx = MarketContext(now=_dt(close_ts), snapshot=snap, candles=window, score=score,
                                history=s.snapshots[: ss.snap_idx], timeframe_s=s.timeframe_s, reduced=reduced)
            for strat in self.strategies:
                dec = strat.evaluate(ctx)
                if dec.signal is None:
                    continue
                n_signals += 1
                reserve = snap.liquidity_quote
                rd = self.risk.check_entry(port, dec.signal, now=ctx.now, reserve_sol=reserve, fee_pct=dex_fee(s.dex_id))
                if not rd.allowed:
                    for r in rd.reasons[:1]:
                        counters[f"rifiutato dal risk manager: {r.split('(')[0].strip()}"] += 1
                    break
                atr_v = ind.atr(window, 14)
                ss.pending_entry = (dec.signal, rd.size_sol, atr_v)
                break

        # close anything still open at the end of data
        for ss in states.values():
            if ss.position is not None:
                self._execute_exit(ss, ss.position.qty, ss.last_close, "END_OF_DATA", _dt(ss.last_ts), port)
        final_equity = self._equity(states, port)
        if events:
            curve.append((_dt(events[-1][0]), final_equity))

        metrics = compute_metrics(self.trades, curve, cfg.initial_capital_sol, max_capital_used=self._capital_used,
                                  failed_orders=self._failed)
        return BacktestResult(
            config=cfg, metrics=metrics, trades=self.trades, equity_curve=curve, signals=n_signals,
            rejections=dict(counters), warnings=warnings, data_info=asdict(ds.info),
        )


def run_backtest(ds: Dataset, cfg: BacktestConfig) -> BacktestResult:
    return BacktestEngine(cfg).run(ds)
