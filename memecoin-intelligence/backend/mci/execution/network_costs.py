"""Real network costs measured from free public sources (no paid service).

* priority fees: ``getRecentPrioritizationFees`` for the pump.fun program accounts (micro-lamports per CU of the
  last ~150 slots) -> SOL for a typical swap of 200k compute units;
* Jito tip floor: the public block-engine statistics endpoint (landed tips percentiles, in SOL).

Paper fills use max(configured fee, measured 75th percentile): measurements can only make the simulation more
conservative, never cheaper than what the owner configured.
"""

from __future__ import annotations

from typing import Any

import httpx

from mci.chain.pump import PUMP_PROGRAM_ID
from mci.chain.rpc_pool import RpcPool
from mci.domain import utcnow

TIP_FLOOR_URL = "https://bundles.jito.wtf/api/v1/bundles/tip_floor"
SWAP_CU = 200_000
MAX_PRIORITY_SOL = 0.005


def _pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    vals = sorted(vals)
    k = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return vals[k]


async def measure(rpc: RpcPool, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"measured_at": utcnow().isoformat(), "swap_cu": SWAP_CU}
    try:
        fees = await rpc.priority_fees([PUMP_PROGRAM_ID])
        nz = [f for f in fees if f > 0]
        out["slots"] = len(fees)
        out["nonzero_share"] = round(len(nz) / len(fees), 3) if fees else None
        for name, q in (("p50", 0.5), ("p75", 0.75), ("p90", 0.9)):
            v = _pct([float(x) for x in fees], q)
            out[f"priority_{name}_sol"] = round(v * SWAP_CU / 1e6 / 1e9, 9) if v is not None else None
    except Exception as e:  # measurement is optional
        out["priority_error"] = str(e)[:120]
    own = client is None
    client = client or httpx.AsyncClient(timeout=15)
    try:
        r = await client.get(TIP_FLOOR_URL)
        data = r.json()
        row = data[0] if isinstance(data, list) and data else {}
        for name in ("25th", "50th", "75th", "95th"):
            v = row.get(f"landed_tips_{name}_percentile")
            out[f"jito_{name[:2]}_sol"] = float(v) if isinstance(v, (int, float)) else None
    except Exception as e:
        out["jito_error"] = str(e)[:120]
    finally:
        if own:
            await client.aclose()
    return out


def effective_priority_fee(configured: float, measured: dict[str, Any] | None) -> float:
    m = (measured or {}).get("priority_p75_sol")
    if not isinstance(m, (int, float)):
        return configured
    return round(min(max(configured, float(m)), MAX_PRIORITY_SOL), 9)
