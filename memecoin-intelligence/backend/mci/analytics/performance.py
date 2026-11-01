"""Performance analytics computed from the database (shared by API, Telegram and reports)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mci.backtesting.metrics import max_drawdown
from mci.database import repo
from mci.database.models import EquitySnapshot, Order, Position, SignalRow
from mci.domain import to_utc, utcnow


def position_dict(p: Position, sol_eur: float | None = None) -> dict[str, Any]:
    cur = p.last_price
    value = (p.qty * cur) if (cur is not None and p.status == "open") else None
    unreal = (p.proceeds_sol + value - p.cost_sol) if value is not None else None
    pnl = p.realized_pnl_sol if p.status == "closed" else unreal
    end = to_utc(p.closed_at) or utcnow()
    return {
        "id": p.id,
        "mode": p.mode,
        "token": p.token_address,
        "symbol": p.symbol,
        "strategy": p.strategy,
        "status": p.status,
        "opened_at": to_utc(p.opened_at).isoformat() if p.opened_at else None,
        "closed_at": to_utc(p.closed_at).isoformat() if p.closed_at else None,
        "entry_price": p.entry_price,
        "current_price": cur,
        "stake_sol": p.stake_sol,
        "cost_sol": p.cost_sol,
        "qty": p.qty,
        "qty_initial": p.qty_initial,
        "stop_price": p.stop_price,
        "take_profits": p.take_profits,
        "pnl_sol": pnl,
        "pnl_eur": pnl * sol_eur if (pnl is not None and sol_eur) else None,
        "return_pct": (pnl / p.cost_sol) if (pnl is not None and p.cost_sol) else None,
        "fees_sol": p.fees_sol,
        "slippage_sol": p.slippage_sol,
        "duration_min": (end - to_utc(p.opened_at)).total_seconds() / 60 if p.opened_at else None,
        "exit_reason": p.exit_reason,
        "score": p.score,
    }


def summary(s: Session, mode: str, initial: float, sol_eur: float | None = None) -> dict[str, Any]:
    closed = repo.closed_positions(s, mode)
    opened = repo.open_positions(s, mode)
    state = repo.get_state(s, f"portfolio_{mode}") or {}
    pnl = [p.realized_pnl_sol or 0.0 for p in closed]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    gl = -sum(losses)
    eq_rows = s.scalars(select(EquitySnapshot).where(EquitySnapshot.mode == mode).order_by(EquitySnapshot.ts.asc())).all()
    equity_curve = [(to_utc(r.ts), r.equity_sol) for r in eq_rows]
    equity = state.get("equity", initial)
    cash = state.get("cash", initial)
    invested = sum(p.cost_sol - p.proceeds_sol for p in opened)
    peak = max([initial] + [v for _, v in equity_curve] + [equity])
    return {
        "mode": mode,
        "initial_capital_sol": initial,
        "equity_sol": equity,
        "cash_sol": cash,
        "invested_sol": invested,
        "net_profit_sol": equity - initial,
        "roi": equity / initial - 1 if initial else 0,
        "drawdown": 1 - equity / peak if peak > 0 else 0,
        "max_drawdown": max_drawdown([v for _, v in equity_curve] + [equity]),
        "win_rate": len(wins) / len(pnl) if pnl else None,
        "profit_factor": (sum(wins) / gl) if gl > 0 else None,
        "total_trades": len(closed),
        "open_positions": len(opened),
        "avg_win_sol": sum(wins) / len(wins) if wins else None,
        "avg_loss_sol": sum(losses) / len(losses) if losses else None,
        "expectancy_sol": sum(pnl) / len(pnl) if pnl else None,
        "fees_sol": sum(p.fees_sol for p in closed + opened),
        "slippage_sol": sum(p.slippage_sol for p in closed + opened),
        "sol_eur": sol_eur,
        "equity_eur": equity * sol_eur if sol_eur else None,
        "kill_switch": state.get("kill_switch", False),
        "kill_reason": state.get("kill_reason", ""),
        "paused": bool(repo.get_state(s, "control_paused", False)),
    }


def period_pnl(s: Session, mode: str, bucket: str = "day") -> list[dict[str, Any]]:
    out: dict[str, float] = defaultdict(float)
    for p in repo.closed_positions(s, mode):
        t = to_utc(p.closed_at)
        if bucket == "day":
            k = t.date().isoformat()
        elif bucket == "week":
            iso = t.isocalendar()
            k = f"{iso.year}-W{iso.week:02d}"
        else:
            k = f"{t.year}-{t.month:02d}"
        out[k] += p.realized_pnl_sol or 0.0
    return [{"period": k, "pnl_sol": v} for k, v in sorted(out.items())]


def by_strategy(s: Session, mode: str) -> list[dict[str, Any]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for p in repo.closed_positions(s, mode):
        groups[p.strategy].append(p.realized_pnl_sol or 0.0)
    rows = []
    for k, v in sorted(groups.items()):
        w = [x for x in v if x > 0]
        gl = -sum(x for x in v if x <= 0)
        rows.append({"strategy": k, "trades": len(v), "pnl_sol": sum(v), "win_rate": len(w) / len(v),
                     "profit_factor": (sum(w) / gl) if gl > 0 else None})
    return rows


def returns_distribution(s: Session, mode: str) -> list[float]:
    return [((p.realized_pnl_sol or 0.0) / p.cost_sol) for p in repo.closed_positions(s, mode) if p.cost_sol]


def day_stats(s: Session, mode: str, day_start: datetime) -> dict[str, Any]:
    end = day_start + timedelta(days=1)
    closed = [p for p in repo.closed_positions(s, mode, since=day_start) if to_utc(p.closed_at) < end]
    orders = s.scalars(select(Order).where(Order.mode == mode, Order.created_at >= day_start, Order.created_at < end,
                                           Order.status == "filled")).all()
    pnl = [p.realized_pnl_sol or 0.0 for p in closed]
    best = max(closed, key=lambda p: p.realized_pnl_sol or 0, default=None)
    worst = min(closed, key=lambda p: p.realized_pnl_sol or 0, default=None)

    def lbl(p: Position | None) -> str:
        if p is None:
            return "n/d"
        r = (p.realized_pnl_sol or 0) / p.cost_sol if p.cost_sol else 0
        return f"{p.symbol} {r * 100:+.1f}% ({p.realized_pnl_sol or 0:+.4f} SOL)"

    signals = s.scalars(select(SignalRow).where(SignalRow.created_at >= day_start, SignalRow.created_at < end)).all()
    return {
        "buys": sum(1 for o in orders if o.side == "buy"),
        "sells": sum(1 for o in orders if o.side == "sell"),
        "wins": sum(1 for x in pnl if x > 0),
        "losses": sum(1 for x in pnl if x <= 0),
        "daily_pnl_closed_sol": sum(pnl),
        "fees_sol": sum(p.fees_sol for p in closed),
        "best": lbl(best),
        "worst": lbl(worst),
        "signals": len(signals),
    }
