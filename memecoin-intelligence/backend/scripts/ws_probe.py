"""Probe 2: can we get pump.fun trades for free from the public Solana WebSocket (logsSubscribe)?

Measures messages/s, bytes/s and decodes the official TradeEvent/CreateEvent from the logs. Then reconstructs the
early buyers of one freshly created (non-mayhem) token via RPC and tries a Jupiter sell simulation from a real
holder. Read-only.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import struct
import sys
import time
from pathlib import Path

import httpx

WS = os.environ.get("PROBE_WS_URL", "wss://api.mainnet-beta.solana.com")
RPC = os.environ.get("PROBE_RPC_URL", "https://api.mainnet-beta.solana.com")
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
TRADE = bytes.fromhex("bddb7fd34ee661ee")
CREATE = bytes.fromhex("1b72a94ddeeb6376")
SOL_MINT = "So11111111111111111111111111111111111111112"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
OUT.mkdir(parents=True, exist_ok=True)
res: dict = {}
A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = A[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def trade(b: bytes) -> dict:
    o = 8
    mint = b58(b[o:o + 32]); o += 32
    sol, tok = struct.unpack_from("<QQ", b, o); o += 16
    is_buy = b[o] != 0; o += 1
    user = b58(b[o:o + 32]); o += 32
    ts, vsol, vtok, rsol, rtok = struct.unpack_from("<qQQQQ", b, o)
    return {"mint": mint, "sol": sol, "tok": tok, "buy": is_buy, "user": user, "ts": ts, "vsol": vsol, "vtok": vtok,
            "rsol": rsol, "rtok": rtok}


def create(b: bytes) -> dict:
    o = 8
    out = {}
    for k in ("name", "symbol", "uri"):
        n = struct.unpack_from("<I", b, o)[0]; o += 4
        out[k] = b[o:o + n].decode("utf-8", "replace"); o += n
    for k in ("mint", "bonding_curve", "user", "creator"):
        out[k] = b58(b[o:o + 32]); o += 32
    out["ts"] = struct.unpack_from("<q", b, o)[0]
    return out


async def firehose(seconds: int = 60) -> dict:
    import websockets

    stats = {"msgs": 0, "bytes": 0, "trades": 0, "creates": 0, "errors": 0, "users": set(), "mints": set()}
    samples = []
    created = []
    async with websockets.connect(WS, ping_interval=20, max_size=2**23) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                                  "params": [{"mentions": [PUMP]}, {"commitment": "confirmed"}]}))
        t0 = time.time()
        while time.time() - t0 < seconds:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                continue
            stats["msgs"] += 1
            stats["bytes"] += len(raw)
            msg = json.loads(raw)
            val = (((msg.get("params") or {}).get("result") or {}).get("value") or {})
            if val.get("err"):
                stats["errors"] += 1
                continue
            for line in val.get("logs") or []:
                if not line.startswith("Program data: "):
                    continue
                try:
                    b = base64.b64decode(line[14:])
                except Exception:  # noqa: BLE001
                    continue
                if b[:8] == TRADE:
                    t = trade(b)
                    stats["trades"] += 1
                    stats["users"].add(t["user"])
                    stats["mints"].add(t["mint"])
                    if len(samples) < 40:
                        samples.append({"sig": val.get("signature"), "slot": msg["params"]["result"]["context"]["slot"], **t})
                elif b[:8] == CREATE:
                    stats["creates"] += 1
                    c = create(b)
                    c["slot"] = msg["params"]["result"]["context"]["slot"]
                    created.append(c)
        el = time.time() - t0
    out = {k: (len(v) if isinstance(v, set) else v) for k, v in stats.items()}
    out.update(seconds=round(el, 1), msgs_per_s=round(stats["msgs"] / el, 1), kb_per_s=round(stats["bytes"] / el / 1024, 1))
    (OUT / "ws_trades_sample.json").write_text(json.dumps(samples, indent=1))
    (OUT / "ws_creates_sample.json").write_text(json.dumps(created[:30], indent=1))
    out["created_list"] = created
    return out


async def rpc(http: httpx.AsyncClient, method: str, params: list) -> dict:
    for attempt in range(5):
        r = await http.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if r.status_code == 429:
            await asyncio.sleep(3 + 3 * attempt)
            continue
        body = r.json()
        await asyncio.sleep(0.7)
        if "error" in body:
            raise RuntimeError(f"{method}: {body['error']}")
        return body["result"]
    raise RuntimeError(f"{method}: rate limited")


async def main() -> None:
    try:
        fh = await firehose()
        created = fh.pop("created_list")
        res["firehose"] = fh
        print("FIREHOSE", fh, flush=True)
    except Exception as e:  # noqa: BLE001
        res["firehose_error"] = repr(e)
        created = []
        print("FIREHOSE ERR", repr(e), flush=True)
    await asyncio.sleep(90)  # let the new tokens collect their first buyers
    async with httpx.AsyncClient(timeout=30) as http:
        jito = (await http.post("https://mainnet.block-engine.jito.wtf/api/v1/getTipAccounts",
                                json={"jsonrpc": "2.0", "id": 1, "method": "getTipAccounts", "params": []})).json()
        tips = set(jito.get("result") or [])
        best = None
        for c in created[:8]:
            try:
                sigs = await rpc(http, "getSignaturesForAddress", [c["bonding_curve"], {"limit": 100}])
            except Exception as e:  # noqa: BLE001
                res.setdefault("errors", []).append(repr(e))
                continue
            if best is None or len(sigs) > len(best[1]):
                best = (c, sigs)
        if not best:
            (OUT / "ws_probe.json").write_text(json.dumps(res, indent=1))
            return
        c, sigs = best
        early = list(reversed(sigs))[:15]
        txs = []
        for s in early:
            tx = await rpc(http, "getTransaction", [s["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
            txs.append(tx)
        (OUT / "early_txs_normal.json").write_text(json.dumps({"create": c, "txs": txs}, indent=1)[:5_000_000])
        rows = []
        net: dict[str, int] = {}
        for tx in txs:
            if not tx:
                continue
            meta, msg = tx["meta"], tx["transaction"]["message"]
            ixs = msg["instructions"] + [i for g in (meta.get("innerInstructions") or []) for i in g["instructions"]]
            tip = sum(i["parsed"]["info"]["lamports"] for i in ixs if i.get("program") == "system"
                      and (i.get("parsed") or {}).get("type") == "transfer" and i["parsed"]["info"].get("destination") in tips)
            for line in meta.get("logMessages") or []:
                if line.startswith("Program data: "):
                    b = base64.b64decode(line[14:])
                    if b[:8] == TRADE:
                        t = trade(b)
                        net[t["user"]] = net.get(t["user"], 0) + (t["tok"] if t["buy"] else -t["tok"])
                        rows.append({"slot": tx["slot"], "payer": msg["accountKeys"][0]["pubkey"], "user": t["user"],
                                     "buy": t["buy"], "sol": t["sol"] / 1e9, "tok": t["tok"], "jito_tip": tip / 1e9,
                                     "cu_price_ix": sum(1 for i in msg["instructions"] if i.get("programId", "").startswith("ComputeBudget"))})
        res["early"] = {"mint": c["mint"], "create_slot": c["slot"], "creator": c["creator"], "rows": rows}
        print("EARLY", json.dumps(res["early"])[:3000], flush=True)
        # sell simulation from the largest current holder that is a normal wallet with SOL
        holders = sorted(((u, n) for u, n in net.items() if n > 0 and u != c["bonding_curve"]), key=lambda x: -x[1])
        for user, amount in holders[:5]:
            bal = await rpc(http, "getBalance", [user])
            if (bal or {}).get("value", 0) < 5_000_000:
                continue
            q = await http.get("https://lite-api.jup.ag/swap/v1/quote", params={
                "inputMint": c["mint"], "outputMint": SOL_MINT, "amount": str(max(1, amount // 10)), "slippageBps": "1500"})
            quote = q.json()
            sim = None
            if q.status_code == 200 and "routePlan" in quote:
                await asyncio.sleep(1.2)
                sw = (await http.post("https://lite-api.jup.ag/swap/v1/swap", json={
                    "quoteResponse": quote, "userPublicKey": user, "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True})).json()
                if sw.get("swapTransaction"):
                    sim = await rpc(http, "simulateTransaction", [sw["swapTransaction"], {
                        "encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True, "commitment": "processed"}])
            res["sell_sim"] = {"user": user, "quote_status": q.status_code, "route": [r.get("swapInfo", {}).get("label")
                                                                                     for r in quote.get("routePlan", [])],
                               "quote_err": None if "routePlan" in quote else str(quote)[:300],
                               "sim_err": ((sim or {}).get("value") or {}).get("err"),
                               "sim_units": ((sim or {}).get("value") or {}).get("unitsConsumed"),
                               "sim_logs_tail": (((sim or {}).get("value") or {}).get("logs") or [])[-6:]}
            print("SELL_SIM", json.dumps(res["sell_sim"])[:1500], flush=True)
            break
    (OUT / "ws_probe.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    asyncio.run(main())
