"""Holder concentration fallback from raw RPC data (used when RugCheck is unavailable).

``getTokenLargestAccounts`` returns *token accounts*, not owners, and includes pool
vaults / bonding curve accounts. Accounts in ``exclude`` are removed before computing
concentration. The result is flagged ``approximate`` because without owner resolution
the same entity can appear as several accounts (concentration is under-estimated) or a
pool vault may not be recognized (concentration is over-estimated).
"""

from __future__ import annotations

from typing import Any

# Well-known AMM authority (Raydium AMM v4). Additional addresses are passed per token.
KNOWN_NON_HOLDERS = {
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
    "1nc1nerator11111111111111111111111111111111",
}


def concentration_from_accounts(
    accounts: list[dict[str, Any]], total_supply_ui: float, exclude: set[str] | None = None
) -> dict[str, Any]:
    if not total_supply_ui or total_supply_ui <= 0:
        return {"top1_pct": None, "top10_pct": None, "approximate": True}
    excl = KNOWN_NON_HOLDERS | (exclude or set())
    vals = sorted(
        (float(a.get("ui_amount") or 0.0) for a in accounts if a.get("address") not in excl),
        reverse=True,
    )
    if not vals:
        return {"top1_pct": None, "top10_pct": None, "approximate": True}
    return {
        "top1_pct": 100.0 * vals[0] / total_supply_ui,
        "top10_pct": 100.0 * sum(vals[:10]) / total_supply_ui,
        "approximate": True,
    }
