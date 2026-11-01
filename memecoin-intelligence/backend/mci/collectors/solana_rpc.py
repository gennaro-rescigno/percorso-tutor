"""Minimal Solana JSON-RPC client (standard methods only)."""

from __future__ import annotations

from typing import Any

from mci.utils.http import ApiClient, SourceUnavailable, fnum, inum


class SolanaRpc:
    def __init__(self, url: str, rps: float = 2.0, client: ApiClient | None = None):
        self.api = client or ApiClient("solana_rpc", url, rate_per_s=rps, burst=3)
        self._id = 0

    async def close(self) -> None:
        await self.api.close()

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        self._id += 1
        data = await self.api.post("", json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or []})
        if not isinstance(data, dict):
            raise SourceUnavailable("solana_rpc", "invalid response")
        if data.get("error"):
            raise SourceUnavailable("solana_rpc", f"rpc error: {data['error'].get('message', '?')}")
        return data.get("result")

    async def mint_info(self, mint: str) -> dict[str, Any] | None:
        res = await self.call("getAccountInfo", [mint, {"encoding": "jsonParsed"}])
        value = (res or {}).get("value")
        if not value:
            return None
        parsed = ((value.get("data") or {}).get("parsed") or {}) if isinstance(value.get("data"), dict) else {}
        info = parsed.get("info") or {}
        return {
            "program": value.get("owner"),
            "decimals": inum(info.get("decimals")),
            "supply": inum(info.get("supply")),
            "mint_authority": info.get("mintAuthority"),
            "freeze_authority": info.get("freezeAuthority"),
            "extensions": [e.get("extension") for e in (info.get("extensions") or []) if isinstance(e, dict)],
        }

    async def largest_accounts(self, mint: str) -> list[dict[str, Any]]:
        res = await self.call("getTokenLargestAccounts", [mint])
        out = []
        for v in (res or {}).get("value") or []:
            out.append({"address": v.get("address"), "ui_amount": fnum(v.get("uiAmount")) or 0.0})
        return out

    async def balance_sol(self, pubkey: str) -> float:
        res = await self.call("getBalance", [pubkey, {"commitment": "confirmed"}])
        return (inum((res or {}).get("value")) or 0) / 1_000_000_000

    async def token_balance_raw(self, owner: str, mint: str) -> int:
        res = await self.call(
            "getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed", "commitment": "confirmed"}]
        )
        total = 0
        for acc in (res or {}).get("value") or []:
            amt = (((acc.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info", {})
            total += inum((amt.get("tokenAmount") or {}).get("amount")) or 0
        return total

    async def send_transaction(self, tx_base64: str) -> str:
        return await self.call(
            "sendTransaction", [tx_base64, {"encoding": "base64", "skipPreflight": False, "maxRetries": 2}]
        )

    async def signature_status(self, signature: str) -> dict[str, Any] | None:
        res = await self.call("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
        vals = (res or {}).get("value") or [None]
        return vals[0]
