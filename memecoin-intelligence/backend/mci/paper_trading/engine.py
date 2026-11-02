"""Trading engine (paper by default; the same code path drives live mode).

Per scan cycle:
  candidates -> strategies -> Signal (recorded with the data available at that moment)
  -> RiskManager (limits, sizing) -> Order (idempotent client id) -> Executor -> Fill
  -> Position. Every step is persisted and notified; rejected signals keep their reason.

Position monitor (every few seconds): price refresh -> exit engine -> sell orders.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select

from mci.collectors.dexscreener import DexScreenerCollector
from mci.config import Settings
from mci.database import repo
from mci.database.models import Order, Position, SignalRow
from mci.database.session import session_scope
from mci.domain import Fill, Signal, TokenSnapshot, to_utc, utcnow
from mci.execution.base import Executor, TradeRequest
from mci.execution.costs import CostModel, dex_fee
from mci.risk_management.exits import EXIT_POLICIES, ExitPolicy, PositionState, evaluate_bar, initial_stop
from mci.risk_management.manager import PortfolioState, RiskManager
from mci.risk_management.profiles import RiskProfile
from mci.scanner.service import Scanner, TrackedToken
from mci.strategies import indicators as ind
from mci.strategies.base import MarketContext, Strategy
from mci.strategies.library import build_strategy
from mci.utils.http import SourceUnavailable

log = logging.getLogger(__name__)

STRATEGY_NAMES = {"A": "Early Entry", "B": "Momentum", "C": "Pullback", "D": "Accumulazione", "E": "Revival"}
# A signal is computed on candles; if their last price is far from the live market price, the data is stale or
# in another unit and the signal is not trustworthy (missing/unverifiable data never becomes a positive signal).
MAX_REFERENCE_DIVERGENCE = 0.20


def price_divergence(reference: float | None, live: float | None) -> float | None:
    if not reference or not live or reference <= 0 or live <= 0:
        return None
    return abs(reference / live - 1)
TF_FACTOR = {"1m": 1, "5m": 5, "15m": 15}


class Notifier(Protocol):
    async def notify(self, kind: str, payload: dict[str, Any]) -> None: ...


class NullNotifier:
    async def notify(self, kind: str, payload: dict[str, Any]) -> None:
        return None


def _pos_state_to_json(ps: PositionState) -> dict[str, Any]:
    d = asdict(ps)
    d["entry_time"] = ps.entry_time.isoformat()
    return d


def _pos_state_from_json(d: dict[str, Any]) -> PositionState:
    d = dict(d)
    d["entry_time"] = datetime.fromisoformat(d["entry_time"])
    return PositionState(**d)


class TradingEngine:
    def __init__(
        self,
        settings: Settings,
        scanner: Scanner,
        executor: Executor,
        profile: RiskProfile,
        costs: CostModel,
        notifier: Notifier | None = None,
        exit_policy: ExitPolicy | None = None,
        strategies: list[Strategy] | None = None,
    ):
        self.s = settings
        self.mode = executor.mode
        self.scanner = scanner
        self.executor = executor
        self.profile = profile
        self.costs = costs
        self.risk = RiskManager(profile, costs)
        self.notifier = notifier or NullNotifier()
        self.policy = exit_policy or EXIT_POLICIES["ladder_trailing"]
        self.strategies = strategies or [build_strategy(c) for c in settings.strategies]
        self.port = self._load_portfolio()
        self.last_equity_notified = self.port.equity
        self._pending_alerts: list[str] = []

    # ------------------------------------------------------------------ state
    @property
    def _state_key(self) -> str:
        return f"portfolio_{self.mode}"

    def _load_portfolio(self) -> PortfolioState:
        with session_scope() as s:
            d = repo.get_state(s, self._state_key)
        if d:
            return PortfolioState.from_dict(d)
        cap = self.s.initial_capital_sol
        return PortfolioState(equity=cap, cash=cap, peak_equity=cap, day_start_equity=cap)

    def _save_portfolio(self, s) -> None:
        repo.set_state(s, self._state_key, self.port.to_dict())

    def _log(self, s, category: str, message: str, **kw) -> None:
        repo.log_event(s, category, message, **kw)

    def _market_anomaly(self) -> str | None:
        return self.scanner.sol_anomaly() or self.scanner.data_outage()

    def control_flags(self) -> tuple[bool, bool]:
        with session_scope() as s:
            paused = bool(repo.get_state(s, "control_paused", False))
            kill = repo.get_state(s, "control_kill", None)
            resume = bool(repo.get_state(s, "control_resume_request", False))
            if kill and not self.port.kill_switch:
                RiskManager.activate_kill_switch(self.port, str(kill))
                repo.set_state(s, "control_kill", None)
            if resume:
                RiskManager.resume(self.port)
                repo.set_state(s, "control_resume_request", False)
                repo.log_event(s, "risk", "trading ripreso manualmente (kill switch disattivato)")
            self._save_portfolio(s)
        return paused, self.port.kill_switch

    # ------------------------------------------------------------------ marks
    def mark_to_market(self, sol_eur: float | None, sol_usd: float | None, record: bool = False) -> float:
        with session_scope() as s:
            value = 0.0
            self.port.exposure = {}
            for p in repo.open_positions(s, self.mode):
                tt = self.scanner.tokens.get(p.token_address)
                if tt and tt.snapshot.price_native:
                    p.last_price = tt.snapshot.price_native
                px = p.last_price or p.entry_price
                value += p.qty * px
                self.port.exposure[p.token_address] = p.qty * px
            equity = self.port.cash + value
            for alert in self.risk.update_equity(self.port, equity, self.port.cash, utcnow()):
                self._log(s, "risk", alert, level="warn")
                self._pending_alerts.append(alert)
            if record:
                repo.add_equity_snapshot(s, self.mode, equity, self.port.cash, value, self.port.drawdown_pct, sol_eur, sol_usd)
            self._save_portfolio(s)
        return equity

    async def flush_alerts(self) -> None:
        while self._pending_alerts:
            await self.notifier.notify("anomaly", {"text": self._pending_alerts.pop(0)})

    # ------------------------------------------------------------------ signals
    def _context(self, tt: TrackedToken, strat: Strategy) -> MarketContext | None:
        tf = strat.default_timeframe
        if tf == "1h":
            candles = tt.candles.get("1h") or []
        else:
            base = tt.candles.get("1m") or []
            candles = ind.resample(base, TF_FACTOR.get(tf, 1)) if base else []
            if candles and len(candles) > 1:
                candles = candles[:-1]  # drop the still-forming candle
        return MarketContext(
            now=utcnow(), snapshot=tt.snapshot, candles=candles, score=tt.trade_score,
            history=list(tt.history), timeframe_s={"1m": 60, "5m": 300, "15m": 900, "1h": 3600}.get(tf, 60),
        )

    async def on_scan(self, candidates: list[TrackedToken]) -> None:
        paused, killed = self.control_flags()
        anomaly = self._market_anomaly()
        price = self.scanner.fx.last
        sol_eur = price.eur if price else None
        await self._token_alerts(candidates)
        if paused:
            return
        with session_scope() as s:
            open_tokens = {p.token_address for p in repo.open_positions(s, self.mode)}
        for tt in candidates:
            if tt.address in open_tokens or tt.trade_score is None or tt.trade_score.excluded:
                continue
            for strat in self.strategies:
                ctx = self._context(tt, strat)
                if ctx is None:
                    continue
                dec = strat.evaluate(ctx)
                if dec.signal is None:
                    continue
                await self._handle_signal(tt, strat, dec.signal, anomaly, sol_eur, killed)
                break

    async def _token_alerts(self, candidates: list[TrackedToken]) -> None:
        for tt in candidates:
            sc = tt.score
            if sc is None or sc.excluded or sc.total < self.s.telegram_min_score_alert:
                continue
            with session_scope() as s:
                if not repo.should_alert(s, f"score:{tt.address}", self.s.telegram_alert_cooldown_minutes):
                    continue
            await self.notifier.notify("token_alert", {
                "token": tt.address, "symbol": tt.snapshot.symbol, "score": sc.total, "label": sc.label,
                "coverage": sc.coverage, "liquidity_usd": tt.snapshot.liquidity_usd,
                "mcap_usd": tt.snapshot.market_cap_usd or tt.snapshot.fdv_usd,
                "explanations": sc.explanations, "risks": sc.risks,
            })

    async def _handle_signal(self, tt: TrackedToken, strat: Strategy, sig: Signal, anomaly: str | None,
                             sol_eur: float | None, killed: bool) -> None:
        snap = tt.snapshot
        fee = dex_fee(snap.dex_id, snap.market_cap_usd)
        with session_scope() as s:
            row = repo.record_signal(s, sig, self.mode, snap, tt.trade_score)
            signal_id = row.id
            rd = self.risk.check_entry(self.port, sig, now=utcnow(), reserve_sol=snap.liquidity_quote, fee_pct=fee,
                                       market_anomaly=anomaly)
            div = price_divergence(sig.reference_price, snap.price_native)
            if div is not None and div > MAX_REFERENCE_DIVERGENCE:
                rd.allowed = False
                rd.reasons = list(rd.reasons) + [f"prezzo delle candele incoerente con il prezzo attuale ({div:.0%})"]
            if not rd.allowed:
                row.status = "rejected"
                row.rejection_reason = "; ".join(rd.reasons)
                self._log(s, "signal", f"segnale {sig.strategy} su {sig.symbol} rifiutato: {row.rejection_reason}",
                               token=sig.token_address)
            else:
                row.status = "accepted"
                self._log(s, "signal", f"segnale {sig.strategy} su {sig.symbol} accettato: {rd.size_sol:.4f} SOL",
                               token=sig.token_address)
        await self.notifier.notify("signal", {
            "symbol": sig.symbol, "strategy_name": STRATEGY_NAMES.get(sig.strategy, sig.strategy), "score": sig.score,
            "price": sig.reference_price, "reasons": sig.reasons, "status": "accettato" if rd.allowed else "rifiutato",
            "rejection": None if rd.allowed else "; ".join(rd.reasons[:2]),
        })
        if rd.allowed:
            await self._open_position(tt, strat, sig, signal_id, rd.size_sol, rd.sizing.risk_sol if rd.sizing else 0.0,
                                      sol_eur)

    async def _open_position(self, tt: TrackedToken, strat: Strategy, sig: Signal, signal_id: int, size: float,
                             risk_sol: float, sol_eur: float | None) -> None:
        snap = tt.snapshot
        coid = f"{self.mode}-buy-{sig.token_address[:12]}-{sig.strategy}-{utcnow():%Y%m%d%H%M}"
        with session_scope() as s:
            if repo.find_order(s, coid):
                self._log(s, "order", f"ordine duplicato ignorato {coid}", level="warn")
                return
            order = Order(client_order_id=coid, mode=self.mode, side="buy", token_address=sig.token_address,
                          signal_id=signal_id, status="submitted", requested_sol=size, reason=f"strategia {sig.strategy}")
            s.add(order)
            s.flush()
            order_id = order.id
        req = TradeRequest(token=sig.token_address, side="buy", sol_amount=size, reference_price=sig.reference_price,
                           dex_id=snap.dex_id, reserve_sol=snap.liquidity_quote, market_cap_usd=snap.market_cap_usd,
                           first_buy=True, slippage_bps=self.s.default_slippage_bps, client_order_id=coid)
        res = await self.executor.execute(req)
        with session_scope() as s:
            order = s.get(Order, order_id)
            sigrow = s.get(SignalRow, signal_id) if signal_id is not None else None
            if not res.ok or res.fill is None or res.fill.qty <= 0:
                order.status = "failed"
                order.error = res.error
                if sigrow:
                    sigrow.status = "failed"
                fee_lost = res.fill.network_fee_sol if res.fill else 0.0
                self.port.cash -= fee_lost
                self._log(s, "order", f"acquisto {sig.symbol} fallito: {res.error}", level="warn",
                               token=sig.token_address)
                self._save_portfolio(s)
                failed = True
            else:
                failed = False
                f: Fill = res.fill
                order.status = "filled"
                order.quote = res.quote
                order.tx_signature = res.tx_signature
                repo.add_fill(s, order, f)
                total_cost = f.sol_amount + f.network_fee_sol + f.rent_sol
                self.port.cash -= total_cost
                closes = tt.candles.get("1m") or []
                atr_v = ind.atr(closes[-60:], 14) if len(closes) > 20 else None
                atr_sol = atr_v * (f.price / closes[-1].close) if (atr_v and closes and closes[-1].close) else None
                stop = initial_stop(self.policy, f.price, sig.stop_price * f.price / sig.reference_price
                                    if sig.reference_price else None, atr_sol)
                vref = (sum(c.volume for c in closes[-20:]) / len(closes[-20:])) if closes else None
                ps = PositionState(
                    token=sig.token_address, strategy=sig.strategy, entry_time=utcnow(), entry_price=f.price,
                    qty_initial=f.qty, qty=f.qty, cost_sol=total_cost, stop_price=stop, initial_stop=stop,
                    high_water=f.price, entry_volume_ref=vref, entry_reserve_sol=snap.liquidity_quote,
                    fees_sol=f.dex_fee_sol + f.network_fee_sol, slippage_sol=max(0.0, f.slippage_sol),
                )
                tps = [{"price": f.price * (1 + g), "fraction": fr, "gain": g} for g, fr in self.policy.take_profits]
                pos = Position(
                    mode=self.mode, token_address=sig.token_address, symbol=(sig.symbol or "")[:64] or None,
                    pair_address=snap.pair_address, dex_id=(snap.dex_id or "")[:32] or None, strategy=sig.strategy, signal_id=signal_id, entry_price=f.price,
                    qty_initial=f.qty, qty=f.qty, token_decimals=res.extra.get("decimals"), stake_sol=f.sol_amount,
                    cost_sol=total_cost, stop_price=stop, initial_stop=stop, take_profits=tps, last_price=f.price,
                    fees_sol=ps.fees_sol, slippage_sol=ps.slippage_sol, state=_pos_state_to_json(ps), score=sig.score,
                )
                s.add(pos)
                s.flush()
                order.position_id = pos.id
                if sigrow:
                    sigrow.status = "executed"
                self.risk.on_entry(self.port, sig.token_address, f.sol_amount)
                self._save_portfolio(s)
                self._log(s, "trade", f"APERTA {sig.symbol} {f.sol_amount:.4f} SOL @ {f.price:.3e} ({f.quote_source})",
                               token=sig.token_address)
        if failed:
            await self.notifier.notify("anomaly", {"text": f"Acquisto {sig.symbol} non eseguito: {res.error}"})
            return
        tp_text = ", ".join(f"+{g:.0%} ({fr:.0%})" for g, fr in self.policy.take_profits) or "solo trailing"
        if self.policy.trailing_activation_pct is not None:
            tp_text += f"; trailing {self.policy.trailing_pct:.0%} dopo +{self.policy.trailing_activation_pct:.0%}"
        await self.notifier.notify("buy", {
            "token": sig.token_address, "symbol": sig.symbol, "strategy_name": STRATEGY_NAMES.get(sig.strategy),
            "entry_price": f.price, "mcap_usd": snap.market_cap_usd or snap.fdv_usd, "liquidity_usd": snap.liquidity_usd,
            "score": sig.score, "stake_sol": f.sol_amount, "allocation_pct": f.sol_amount / max(self.port.equity, 1e-9),
            "risk_sol": risk_sol, "stop_price": stop, "stop_pct": stop / f.price - 1, "tp_text": tp_text,
            "impact": f.price_impact_pct, "quote_source": f.quote_source, "reasons": sig.reasons, "risks": sig.risks,
            "sol_eur": sol_eur,
        })

    # ------------------------------------------------------------------ monitoring
    async def monitor_positions(self) -> None:
        with session_scope() as s:
            positions = [(p.id, p.token_address, p.pair_address) for p in repo.open_positions(s, self.mode)]
        if not positions:
            return
        prices: dict[str, TokenSnapshot] = {}
        try:
            pairs = await self.scanner.dex.pairs_for_tokens(self.s.chain, [t for _, t, _ in positions])
            for addr, p in DexScreenerCollector.best_pair_per_token(pairs, self.s.chain).items():
                prices[addr] = DexScreenerCollector.pair_to_snapshot(p)
        except SourceUnavailable as e:
            log.info("price refresh failed: %s", e)
        fxp = self.scanner.fx.last
        sol_usd = fxp.usd if fxp else None
        for pid, token, _ in positions:
            snap = prices.get(token)
            tt = self.scanner.tokens.get(token)
            px = None
            reserve = None
            if snap is not None:
                px = snap.price_native or (snap.price_usd / sol_usd if (snap.price_usd and sol_usd) else None)
                reserve = snap.liquidity_quote or (snap.liquidity_usd / 2 / sol_usd if (snap.liquidity_usd and sol_usd) else None)
                if tt:
                    tt.snapshot.price_native = px or tt.snapshot.price_native
                    tt.snapshot.liquidity_quote = reserve or tt.snapshot.liquidity_quote
            elif tt:
                px = tt.snapshot.price_native
                reserve = tt.snapshot.liquidity_quote
            if not px:
                continue
            alert = self._onchain_alert(tt)
            await self._check_exit(pid, px, reserve, alert)

    def _onchain_alert(self, tt: TrackedToken | None) -> str | None:
        if tt is None:
            return None
        sn = tt.snapshot
        if sn.rugged_flag:
            return "token segnalato come rug"
        if sn.sell_route_ok is False:
            return "rotta di vendita scomparsa"
        if sn.mint_authority_revoked is False or sn.freeze_authority_revoked is False:
            return "permessi del token modificati (authority attiva)"
        if any((r.get("level") == "danger") for r in sn.rugcheck_risks):
            return "nuovi rischi critici RugCheck"
        wash = sn.social_metrics.get("coordinated_selling")
        if wash:
            return "vendite coordinate dei top holder"
        return None

    async def _check_exit(self, pid: int, px: float, reserve: float | None, alert: str | None) -> None:
        with session_scope() as s:
            p = s.get(Position, pid)
            if p is None or p.status != "open":
                return
            ps = _pos_state_from_json(p.state)
            p.last_price = px
            tt = self.scanner.tokens.get(p.token_address)
            vavg = None
            if tt and tt.candles.get("1m"):
                last = tt.candles["1m"][-5:]
                vavg = sum(c.volume for c in last) / len(last)
            actions = evaluate_bar(ps, self.policy, now=utcnow(), open_=px, high=px, low=px, close=px,
                                   bar_volume_avg=vavg, reserve_sol=reserve, onchain_alert=alert)
            p.state = _pos_state_to_json(ps)
            p.stop_price = max(ps.stop_price, ps.pending_stop or 0)
            info = (p.symbol, p.token_address, p.dex_id, p.token_decimals)
        for a in actions:
            await self._sell(pid, a.qty, px, a.reason, a.description, reserve, info, alert)

    async def _sell(self, pid: int, qty: float, px: float, reason: str, desc: str, reserve: float | None,
                    info: tuple, alert: str | None) -> None:
        symbol, token, dex_id, decimals = info
        coid = f"{self.mode}-sell-{pid}-{reason}-{utcnow():%Y%m%d%H%M%S}"
        with session_scope() as s:
            p = s.get(Position, pid)
            if p is None or p.status != "open" or p.qty <= 0:
                return
            qty = min(qty, p.qty)
            closing = qty >= p.qty - 1e-12
            order = Order(client_order_id=coid, mode=self.mode, side="sell", token_address=token, position_id=pid,
                          status="submitted", requested_qty=qty, reason=desc)
            s.add(order)
            s.flush()
            oid = order.id
        req = TradeRequest(token=token, side="sell", qty=qty, decimals=decimals, reference_price=px, dex_id=dex_id,
                           reserve_sol=reserve, close_account=closing, slippage_bps=max(self.s.default_slippage_bps, 500),
                           client_order_id=coid)
        res = await self.executor.execute(req)
        notify: tuple[str, dict[str, Any]] | None = None
        with session_scope() as s:
            order = s.get(Order, oid)
            p = s.get(Position, pid)
            if not res.ok or res.fill is None:
                order.status = "failed"
                order.error = res.error
                fee = res.fill.network_fee_sol if res.fill else 0.0
                self.port.cash -= fee
                p.fees_sol += fee
                p.cost_sol += fee
                if reason.startswith("TAKE_PROFIT"):
                    ps = _pos_state_from_json(p.state)  # allow the take profit to trigger again
                    ps.tp_done = max(0, ps.tp_done - 1)
                    p.state = _pos_state_to_json(ps)
                self._log(s, "order", f"vendita {symbol} fallita: {res.error}", level="warn", token=token)
                self._save_portfolio(s)
                if alert or "rug" in (res.error or ""):
                    notify = ("rug", {"symbol": symbol, "reasons": [alert or res.error], "action": "vendita fallita: nuovo tentativo al prossimo controllo"})
            else:
                f = res.fill
                order.status = "filled"
                order.quote = res.quote
                order.tx_signature = res.tx_signature
                repo.add_fill(s, order, f)
                net = f.sol_amount - f.network_fee_sol - f.rent_sol  # rent_sol negative = refund
                self.port.cash += net
                ps = _pos_state_from_json(p.state)
                ps.qty -= f.qty
                p.qty = max(0.0, p.qty - f.qty)
                p.proceeds_sol += net
                p.fees_sol += f.dex_fee_sol + f.network_fee_sol
                p.slippage_sol += max(0.0, f.slippage_sol)
                p.state = _pos_state_to_json(ps)
                if p.qty <= 1e-12 or closing:
                    p.status = "closed"
                    p.closed_at = utcnow()
                    p.realized_pnl_sol = p.proceeds_sol - p.cost_sol
                    reasons = list(dict.fromkeys(((p.exit_reason or "").split(" | ") if p.exit_reason else []) + [desc]))
                    p.exit_reason = " | ".join(reasons)
                    self.risk.on_exit(self.port, token, p.realized_pnl_sol, utcnow(), closed=True)
                    self._log(s, "trade", f"CHIUSA {symbol}: {p.realized_pnl_sol:+.4f} SOL ({desc})", token=token)
                    notify = ("close", {
                        "symbol": symbol, "entry_price": p.entry_price, "exit_price": f.price, "stake_sol": p.stake_sol,
                        "proceeds_sol": p.proceeds_sol,
                        "gross_pnl_sol": p.realized_pnl_sol + p.fees_sol,  # before fees (slippage included)
                        "fees_sol": p.fees_sol, "slippage_sol": p.slippage_sol, "net_pnl_sol": p.realized_pnl_sol,
                        "return_pct": p.realized_pnl_sol / p.cost_sol if p.cost_sol else None,
                        "hold_minutes": (utcnow() - to_utc(p.opened_at)).total_seconds() / 60,
                        "exit_reasons": reasons, "reason_code": reason,
                    })
                else:
                    p.exit_reason = " | ".join(filter(None, [p.exit_reason, desc]))
                    self.port.exposure[token] = p.qty * px
                    notify = ("partial", {"title": "TAKE PROFIT" if reason.startswith("TAKE") else "VENDITA PARZIALE",
                                          "symbol": symbol, "fraction": f.qty / p.qty_initial if p.qty_initial else 0,
                                          "price": f.price, "proceeds_sol": net,
                                          "new_stop": max(ps.stop_price, ps.pending_stop or 0), "reason": desc})
                self._save_portfolio(s)
        if notify:
            kind, payload = notify
            if kind == "close":
                fxp = self.scanner.fx.last
                payload["sol_eur"] = fxp.eur if fxp else None
                payload["equity_sol"] = self.mark_to_market(payload["sol_eur"], fxp.usd if fxp else None)
                if payload.get("reason_code") in ("STOP_LOSS", "STOP_GAP"):
                    await self.notifier.notify("stop_hit", payload)
            await self.notifier.notify(kind, payload)

    # ------------------------------------------------------------------ outcomes (Fase 14)
    def track_signal_outcomes(self) -> int:
        """Fill forward prices for recorded signals (what happened after each signal)."""
        updated = 0
        now = utcnow()
        with session_scope() as s:
            rows = s.scalars(select(SignalRow).where(SignalRow.outcome_done.is_(False))
                             .where(SignalRow.created_at >= now - timedelta(hours=30))).all()
            for r in rows:
                tt = self.scanner.tokens.get(r.token_address)
                px = tt.snapshot.price_native if tt else None
                age_h = (now - to_utc(r.created_at)).total_seconds() / 3600
                if px and r.reference_price:
                    rel = px / r.reference_price - 1
                    f = dict(r.features or {})
                    f["_max_rel"] = max(f.get("_max_rel", rel), rel)
                    f["_min_rel"] = min(f.get("_min_rel", rel), rel)
                    r.features = f
                    if age_h >= 0.25 and r.price_15m is None:
                        r.price_15m = px
                    if age_h >= 1 and r.price_1h is None:
                        r.price_1h = px
                    if age_h >= 4 and r.price_4h is None:
                        r.price_4h = px
                    if age_h >= 24 and r.price_24h is None:
                        r.price_24h = px
                    r.max_gain_24h = f["_max_rel"]
                    r.max_drawdown_24h = f["_min_rel"]
                    updated += 1
                if age_h >= 24:
                    r.outcome_done = True
        return updated
