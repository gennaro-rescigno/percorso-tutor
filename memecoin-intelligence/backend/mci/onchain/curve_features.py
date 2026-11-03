"""Bonding-curve and buyer-quality features (point in time) from the early trades of a launch.

Facts only, computed from decoded pump.fun TradeEvents with ``ts <= at``. When the stream had a gap in the
window, ``complete`` is False and consumers must treat the trade-count features as unknown, not as zero.

Definitions (all supply percentages are of the token total supply):
* creation-slot buyers: wallets other than the creator buying in the same slot as the create transaction
  (bundles / block-0 snipers);
* sniper buyers: wallets other than the creator buying within the first 3 slots;
* flippers: wallets that both bought and sold inside the window;
* buy HHI: Herfindahl index of the buy volume by wallet (1 = one wallet did all the buying);
* agent trades: executed through pump.fun's mayhem agent program (never counted as organic).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from mci.onchain.launches import LaunchState, LaunchTracker, progress_pct

FEATURE_VERSION = 2  # v2: completeness from the measured stream coverage (>= 97% of the window)
# the public stream drops connections every few seconds; with redundant connections real gaps are short.
# A window counts as complete when data were received for at least 97% of it (the coverage is stored too).
MIN_COVERAGE = 0.97


def curve_features(st: LaunchState, at: float, tracker: LaunchTracker | None = None) -> dict[str, Any]:
    tr = [t for t in st.trades if t.ts <= at]
    age_s = max(at - st.created_ts, 0.0)
    complete = st.source == "stream" and not (st.early_truncated and (not tr or tr[-1].ts <= at))
    coverage = tracker.coverage(st.created_ts, at) if tracker is not None else None
    if coverage is not None and coverage < MIN_COVERAGE:
        complete = False
    organic = [t for t in tr if not t.agent]
    creator = st.creator
    supply = st.total_supply or 1
    buy_by: dict[str, int] = defaultdict(int)
    net_tokens: dict[str, int] = defaultdict(int)
    sold: set[str] = set()
    bought: set[str] = set()
    buy_sol = sell_sol = creator_buy = creator_sell = 0
    for t in organic:
        if t.is_buy:
            buy_by[t.wallet] += t.sol
            net_tokens[t.wallet] += t.tokens
            bought.add(t.wallet)
            buy_sol += t.sol
            if t.wallet == creator:
                creator_buy += t.sol
        else:
            net_tokens[t.wallet] -= t.tokens
            sold.add(t.wallet)
            sell_sol += t.sol
            if t.wallet == creator:
                creator_sell += t.sol
    first_slot = st.slot if st.slot is not None else (min((t.slot for t in tr if t.slot), default=None))
    same_slot = {t.wallet for t in organic if t.is_buy and t.wallet != creator and first_slot is not None
                 and t.slot == first_slot}
    snipers = {t.wallet for t in organic if t.is_buy and t.wallet != creator and first_slot is not None
               and t.slot is not None and t.slot <= first_slot + 2}
    holders = {w: n for w, n in net_tokens.items() if n > 0}
    top = sorted(holders.values(), reverse=True)
    buyers = set(buy_by) - ({creator} if creator else set())
    shares = [v / buy_sol for v in buy_by.values()] if buy_sol else []
    last_p = next((t.price for t in reversed(tr) if t.price), None)
    peak = max((t.price for t in tr if t.price), default=None)
    launch_p = st.launch_price or next((t.price for t in tr if t.price), None)
    recent = [t for t in organic if t.ts > at - 60 and t.is_buy]
    prog = None
    if tr and tr[-1].rtok:
        init = st.initial_real_tokens or 793_100_000 * 10**6
        prog = max(0.0, min(100.0, (init - tr[-1].rtok) / init * 100))

    def pct(x: int) -> float:
        return round(x / supply * 100, 3)

    f: dict[str, Any] = {
        "version": FEATURE_VERSION,
        "complete": complete,
        "stream_coverage": round(coverage, 4) if coverage is not None else None,
        "age_s": round(age_s, 1),
        "mayhem": bool(st.mayhem),
        "n_trades": len(tr),
        "n_buys": sum(1 for t in organic if t.is_buy),
        "n_sells": sum(1 for t in organic if not t.is_buy),
        "agent_trade_share": round(1 - len(organic) / len(tr), 3) if tr else None,
        "unique_buyers": len(buyers),
        "unique_sellers": len(sold - ({creator} if creator else set())),
        "buy_sol": round(buy_sol / 1e9, 4),
        "sell_sol": round(sell_sol / 1e9, 4),
        "net_flow_sol": round((buy_sol - sell_sol) / 1e9, 4),
        "buy_pressure": round(buy_sol / (buy_sol + sell_sol), 3) if (buy_sol + sell_sol) else None,
        "creator_buy_sol": round(creator_buy / 1e9, 4) if creator else None,
        "creator_sold": (creator_sell > 0) if creator else None,
        "creator_sell_sol": round(creator_sell / 1e9, 4) if creator else None,
        "creator_net_pct": pct(max(net_tokens.get(creator, 0), 0)) if creator else None,
        "same_slot_buyers": len(same_slot) if first_slot is not None else None,
        "same_slot_pct": pct(sum(max(net_tokens[w], 0) for w in same_slot)) if first_slot is not None else None,
        "sniper_buyers": len(snipers) if first_slot is not None else None,
        "sniper_pct": pct(sum(max(net_tokens[w], 0) for w in snipers)) if first_slot is not None else None,
        "top_buyer_share": round(max(shares), 3) if shares else None,
        "buy_hhi": round(sum(s * s for s in shares), 3) if shares else None,
        "flippers": len(bought & sold),
        "flipper_share": round(len(bought & sold) / len(bought), 3) if bought else None,
        "trades_per_wallet": round(len(organic) / len({t.wallet for t in organic}), 2) if organic else None,
        "holders_net": len(holders),
        "top1_net_pct": pct(top[0]) if top else None,
        "top10_net_pct": pct(sum(top[:10])) if top else None,
        "progress_pct": round(prog, 2) if prog is not None else None,
        "progress_per_min": round(prog / (age_s / 60), 3) if prog is not None and age_s >= 30 else None,
        "price": last_p,
        "price_change_pct": round((last_p / launch_p - 1) * 100, 2) if last_p and launch_p else None,
        "drawdown_from_peak_pct": round((1 - last_p / peak) * 100, 2) if last_p and peak else None,
        "buys_last_60s": len(recent),
        "buyers_last_60s": len({t.wallet for t in recent}),
    }
    return f


def early_buyers(st: LaunchState, at: float, limit: int = 20) -> list[dict[str, Any]]:
    """First distinct organic buyers (excluding the creator) with their totals, in order of first buy."""
    seen: dict[str, dict[str, Any]] = {}
    for t in st.trades:
        if t.ts > at or t.agent:
            continue
        if t.wallet == st.creator:
            continue
        d = seen.get(t.wallet)
        if d is None:
            if not t.is_buy or len(seen) >= limit:
                continue
            d = seen[t.wallet] = {"wallet": t.wallet, "first_slot": t.slot, "first_ts": t.ts, "buy_sol": 0,
                                  "net_tokens": 0}
        if t.is_buy:
            d["buy_sol"] += t.sol
            d["net_tokens"] += t.tokens
        else:
            d["net_tokens"] -= t.tokens
    return list(seen.values())


def current_progress(st: LaunchState) -> float | None:
    return progress_pct(st)
