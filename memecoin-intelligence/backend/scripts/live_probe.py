"""Live probe: collect REAL samples from free Solana data sources and save them as JSON fixtures.

Parsers for on-chain data (pump.fun bonding curve, Token-2022 extensions, Metaplex metadata, early
transactions, funding transfers, Jito tips, Jupiter sell simulation) are written and tested against these
real payloads instead of formats guessed from documentation. Run by .github/workflows/memecoin-live-probe.yml
(the development sandbox cannot reach Solana). Read-only: nothing is signed or sent.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

RPC = os.environ.get("PROBE_RPC_URL", "https://api.mainnet-beta.solana.com")
PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
METADATA_PROGRAM = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
SOL_MINT = "So11111111111111111111111111111111111111112"
BONK = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
PYUSD = "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo"  # Token-2022 mint with extensions (format sample)
SYSTEM_PROGRAM = "11111111111111111111111111111111"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
OUT.mkdir(parents=True, exist_ok=True)
summary: dict[str, Any] = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": {}}


def save(name: str, data: Any) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=1, default=str)[:4_000_000])


def note(step: str, ok: bool, info: Any = None) -> None:
    summary["steps"][step] = {"ok": ok, "info": info}
    print(("OK  " if ok else "ERR ") + step + (f" — {info}" if info is not None else ""), flush=True)


class Rpc:
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
        self.calls = 0

    async def __call__(self, method: str, params: list[Any]) -> Any:
        for attempt in range(5):
            self.calls += 1
            r = await self.http.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            if r.status_code == 429:
                await asyncio.sleep(2 + 2 * attempt)
                continue
            r.raise_for_status()
            body = r.json()
            if "error" in body:
                raise RuntimeError(f"{method}: {body['error']}")
            await asyncio.sleep(0.6)  # stay far below public limits
            return body.get("result")
        raise RuntimeError(f"{method}: rate limited")


def pda(seeds: list[bytes], program: str) -> str:
    from solders.pubkey import Pubkey

    return str(Pubkey.find_program_address(seeds, Pubkey.from_string(program))[0])


def b58(s: str) -> bytes:
    from solders.pubkey import Pubkey

    return bytes(Pubkey.from_string(s))


async def pumpportal(seconds: int = 150, max_subscribed: int = 25) -> tuple[list[dict], list[dict]]:
    """Subscribe to the trades of each new token IMMEDIATELY at creation (first buyers happen in seconds)."""
    import websockets

    creates: list[dict] = []
    trades: list[dict] = []
    other: list[dict] = []
    async with websockets.connect("wss://pumpportal.fun/api/data", ping_interval=20) as ws:
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        t0 = time.time()
        while time.time() - t0 < seconds and len(trades) < 600:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            except asyncio.TimeoutError:
                continue
            tx = msg.get("txType")
            if tx == "create":
                creates.append(msg)
                if len(creates) <= max_subscribed:
                    await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": [msg["mint"]]}))
            elif tx in ("buy", "sell"):
                trades.append(msg)
            elif len(other) < 20:
                other.append(msg)
    summary["pumpportal_other_messages"] = other[:10]
    return creates, trades


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as http:
        rpc = Rpc(http)

        # 1) PumpPortal: real create + trade events
        creates, trades = [], []
        try:
            creates, trades = await pumpportal()
            save("pumpportal_creates", creates)
            save("pumpportal_trades", trades)
            note("pumpportal", bool(creates), f"{len(creates)} create, {len(trades)} trade, mint con scambi={len({t.get('mint') for t in trades})}")
        except Exception as e:  # noqa: BLE001
            note("pumpportal", False, repr(e))

        # choose the new token with most trades (more early transactions to look at)
        by_mint: dict[str, int] = {}
        for t in trades:
            by_mint[t.get("mint")] = by_mint.get(t.get("mint"), 0) + 1
        normal = {c["mint"] for c in creates if not c.get("is_mayhem_mode")}
        ranked = sorted(by_mint, key=by_mint.get, reverse=True)
        mint = next((m for m in ranked if m in normal), None) or (ranked[0] if ranked else None) \
            or next(iter(normal), None) or (creates[0]["mint"] if creates else None)
        summary["mayhem_share"] = sum(1 for c in creates if c.get("is_mayhem_mode")) / max(len(creates), 1)
        summary["mint"] = mint

        # 2) mint account (jsonParsed) for the new token, BONK (classic SPL) and PYUSD (Token-2022 extensions)
        for name, m in (("mint_new", mint), ("mint_bonk", BONK), ("mint_pyusd", PYUSD)):
            if not m:
                continue
            try:
                acc = await rpc("getAccountInfo", [m, {"encoding": "jsonParsed", "commitment": "confirmed"}])
                save(name, {"mint": m, "result": acc})
                note(name, acc is not None, (acc or {}).get("value", {}).get("owner") if acc else None)
            except Exception as e:  # noqa: BLE001
                note(name, False, repr(e))

        if not mint:
            save("summary", summary)
            return

        # 3) pump.fun bonding curve PDA + raw account, metadata PDA + raw account
        curve = metadata = None
        try:
            curve = pda([b"bonding-curve", b58(mint)], PUMP_PROGRAM)
            acc = await rpc("getAccountInfo", [curve, {"encoding": "base64", "commitment": "confirmed"}])
            save("curve_account", {"mint": mint, "curve": curve, "result": acc,
                                   "create_event_curve_key": next((c.get("bondingCurveKey") for c in creates
                                                                   if c.get("mint") == mint), None)})
            raw = base64.b64decode(acc["value"]["data"][0]) if acc and acc.get("value") else b""
            note("curve_account", bool(raw), f"{curve} len={len(raw)} owner={(acc or {}).get('value', {}).get('owner')}")
        except Exception as e:  # noqa: BLE001
            note("curve_account", False, repr(e))
        try:
            metadata = pda([b"metadata", b58(METADATA_PROGRAM), b58(mint)], METADATA_PROGRAM)
            acc = await rpc("getAccountInfo", [metadata, {"encoding": "base64", "commitment": "confirmed"}])
            save("metadata_account", {"mint": mint, "metadata": metadata, "result": acc})
            note("metadata_account", bool(acc and acc.get("value")), metadata)
        except Exception as e:  # noqa: BLE001
            note("metadata_account", False, repr(e))

        # 4) earliest transactions on the bonding curve (creation + first buys)
        first_buyer = None
        if curve:
            try:
                sigs = await rpc("getSignaturesForAddress", [curve, {"limit": 1000, "commitment": "confirmed"}])
                save("curve_signatures", {"curve": curve, "result": sigs})
                oldest = list(reversed(sigs or []))[:6]
                txs = []
                for s in oldest:
                    tx = await rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                                       "maxSupportedTransactionVersion": 1,
                                                                       "commitment": "confirmed"}])
                    txs.append(tx)
                save("curve_early_txs", {"curve": curve, "mint": mint, "txs": txs})
                payers = []
                for tx in txs:
                    keys = ((tx or {}).get("transaction") or {}).get("message", {}).get("accountKeys") or []
                    if keys:
                        payers.append(keys[0]["pubkey"] if isinstance(keys[0], dict) else keys[0])
                creator = next((c.get("traderPublicKey") for c in creates if c.get("mint") == mint), None)
                first_buyer = next((p for p in payers if p != creator), None)
                note("curve_early_txs", bool(txs), f"{len(sigs or [])} firme, payers={payers[:4]}")
            except Exception as e:  # noqa: BLE001
                note("curve_early_txs", False, repr(e))

        # 5) funding source of the first buyer (oldest transaction of the wallet)
        if first_buyer:
            try:
                sigs = await rpc("getSignaturesForAddress", [first_buyer, {"limit": 1000, "commitment": "confirmed"}])
                oldest = (sigs or [])[-1] if sigs else None
                tx = None
                if oldest:
                    tx = await rpc("getTransaction", [oldest["signature"], {"encoding": "jsonParsed",
                                                                            "maxSupportedTransactionVersion": 1,
                                                                            "commitment": "confirmed"}])
                save("wallet_funding", {"wallet": first_buyer, "n_signatures": len(sigs or []), "oldest_tx": tx})
                note("wallet_funding", tx is not None, f"{first_buyer} firme={len(sigs or [])}")
            except Exception as e:  # noqa: BLE001
                note("wallet_funding", False, repr(e))

        # 6) holders: largest token accounts + owners (jsonParsed)
        try:
            largest = await rpc("getTokenLargestAccounts", [mint, {"commitment": "confirmed"}])
            addrs = [a["address"] for a in (largest or {}).get("value", [])[:10]]
            owners = await rpc("getMultipleAccounts", [addrs, {"encoding": "jsonParsed"}]) if addrs else None
            save("holders", {"mint": mint, "largest": largest, "accounts": owners})
            note("holders", bool(addrs), f"{len(addrs)} conti")
        except Exception as e:  # noqa: BLE001
            note("holders", False, repr(e))

        # 7) Jito tip accounts + tip floor, recent priority fees
        try:
            r = await http.post("https://mainnet.block-engine.jito.wtf/api/v1/getTipAccounts",
                                json={"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})
            tips = r.json()
            r2 = await http.get("https://bundles.jito.wtf/api/v1/bundles/tip_floor")
            save("jito", {"tip_accounts": tips, "tip_floor": r2.json() if r2.status_code == 200 else r2.text[:500]})
            note("jito", r.status_code == 200, f"tip accounts={len((tips or {}).get('result') or [])}, floor={r2.status_code}")
        except Exception as e:  # noqa: BLE001
            note("jito", False, repr(e))
        try:
            fees = await rpc("getRecentPrioritizationFees", [[curve or mint]])
            save("priority_fees", fees)
            note("priority_fees", fees is not None, f"{len(fees or [])} slot")
        except Exception as e:  # noqa: BLE001
            note("priority_fees", False, repr(e))

        # 8) sell simulation via Jupiter + simulateTransaction from a real holder (BONK and the new token)
        for label, m in (("bonk", BONK), ("new", mint)):
            await asyncio.sleep(5)
            try:
                largest = await rpc("getTokenLargestAccounts", [m, {"commitment": "confirmed"}])
                accs = [a for a in (largest or {}).get("value", [])][:15]
                infos = await rpc("getMultipleAccounts", [[a["address"] for a in accs], {"encoding": "jsonParsed"}])
                holders = []
                for a, info in zip(accs, (infos or {}).get("value") or []):
                    parsed = ((info or {}).get("data") or {}).get("parsed", {}).get("info", {})
                    if parsed.get("owner"):
                        holders.append((parsed["owner"], a["amount"]))
                owner_infos = await rpc("getMultipleAccounts", [[h[0] for h in holders], {"encoding": "base64"}])
                seller = None
                for (owner, amount), oi in zip(holders, (owner_infos or {}).get("value") or []):
                    if oi and oi.get("owner") == SYSTEM_PROGRAM and oi.get("lamports", 0) > 10_000_000:
                        seller = (owner, int(amount))
                        break
                if not seller:
                    note(f"sell_sim_{label}", False, "nessun holder con wallet normale e SOL per le fee")
                    continue
                amount = max(1, seller[1] // 1000)
                q = await http.get("https://lite-api.jup.ag/swap/v1/quote", params={
                    "inputMint": m, "outputMint": SOL_MINT, "amount": str(amount), "slippageBps": "1000"})
                quote = q.json()
                if q.status_code != 200 or "routePlan" not in quote:
                    save(f"sell_sim_{label}", {"mint": m, "quote": quote})
                    note(f"sell_sim_{label}", False, f"quote {q.status_code}: {str(quote)[:200]}")
                    continue
                await asyncio.sleep(1.2)
                s = await http.post("https://lite-api.jup.ag/swap/v1/swap", json={
                    "quoteResponse": quote, "userPublicKey": seller[0], "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True})
                swap = s.json()
                tx_b64 = swap.get("swapTransaction")
                sim = await rpc("simulateTransaction", [tx_b64, {"encoding": "base64", "sigVerify": False,
                                                                 "replaceRecentBlockhash": True,
                                                                 "commitment": "processed"}]) if tx_b64 else None
                save(f"sell_sim_{label}", {"mint": m, "seller": seller[0], "amount": amount, "quote": quote,
                                           "swap_keys": sorted(swap.keys()), "simulation": sim})
                err = ((sim or {}).get("value") or {}).get("err")
                note(f"sell_sim_{label}", sim is not None, f"err={err} units={((sim or {}).get('value') or {}).get('unitsConsumed')}")
            except Exception as e:  # noqa: BLE001
                note(f"sell_sim_{label}", False, repr(e))

        summary["rpc_calls"] = rpc.calls
        save("summary", summary)
        print(json.dumps(summary, indent=1, default=str)[:6000])


if __name__ == "__main__":
    asyncio.run(main())
