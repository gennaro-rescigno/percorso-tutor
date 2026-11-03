"""Real-network check of the bot's own on-chain classes (read-only, free): run by memecoin-live-probe.

1. PumpStream with redundant connections for DURATION seconds -> sessions, drops, coverage, decoded trades;
2. for the busiest non-mayhem launch: curve features, own security check, curve account, early-buyer wallets;
3. measured priority fees / Jito tip floor; sell simulation of a real holder; RPC pool health with errors.
"""

import asyncio
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mci.database.session import init_engine  # noqa: E402

init_engine(f"sqlite:///{tempfile.mkdtemp()}/check.db")

from mci.chain.rpc_pool import RpcPool  # noqa: E402
from mci.chain.stream import PumpStream  # noqa: E402
from mci.collectors.jupiter import JupiterCollector  # noqa: E402
from mci.domain import TokenSnapshot, utcnow  # noqa: E402
from mci.execution import network_costs  # noqa: E402
from mci.execution.sell_sim import simulate_holder_sell  # noqa: E402
from mci.onchain.curve_features import curve_features, early_buyers  # noqa: E402
from mci.onchain.launches import LaunchTracker  # noqa: E402
from mci.onchain.service import OnchainService  # noqa: E402

WS = "wss://api.mainnet-beta.solana.com"
RPC = "https://api.mainnet-beta.solana.com"
DURATION = int(os.environ.get("CHECK_SECONDS", "180"))
CONNECTIONS = int(os.environ.get("CHECK_CONNECTIONS", "2"))


def show(title, obj):
    print(f"\n### {title}")
    print(json.dumps(obj, indent=1, default=str)[:6000])


async def main() -> None:
    tracker = LaunchTracker()
    stream = PumpStream(WS, tracker.on_events, connections=CONNECTIONS,
                        on_state=lambda up: (tracker.stream_up if up else tracker.stream_down)())
    t0 = time.time()
    task = asyncio.create_task(stream.run())
    await asyncio.sleep(DURATION)
    stream.stop()
    try:
        await asyncio.wait_for(task, timeout=30)
    except Exception:
        task.cancel()
    t1 = time.time()
    show("stream", stream.health())
    show("sessioni (connessione, secondi, messaggi, motivo)", list(stream.sessions))
    show("lanci", tracker.health())
    print(f"\ncopertura dello stream nella finestra di prova: {tracker.coverage(t0 + 20, t1 - 1, now=t1):.4f}")

    cands = [st for st in tracker.launches.values() if st.source == "stream" and not st.mayhem and st.trades]
    cands.sort(key=lambda st: len(st.trades), reverse=True)
    mayhem = sum(1 for st in tracker.launches.values() if st.mayhem)
    print(f"lanci osservati: {len(tracker.launches)} · mayhem {mayhem} · con operazioni: {len(cands)}")
    pool = RpcPool([RPC], rps=4)
    svc = OnchainService(pool, tracker)
    if cands:
        st = cands[0]
        f = curve_features(st, time.time(), tracker)
        show(f"feature della curva di {st.symbol} ({st.mint})", f)
        snap = TokenSnapshot(chain="solana", token_address=st.mint, observed_at=utcnow(), bonding_curve=True,
                             deployer=st.creator)
        for name, coro in (("sicurezza", svc.security(snap)), ("curva", svc.curve_state(snap))):
            try:
                await coro
            except Exception as e:
                print(f"{name}: ERRORE {type(e).__name__}: {e}")
        show("sicurezza e curva", {"mint_revoked": snap.mint_authority_revoked, "freeze_revoked": snap.freeze_authority_revoked,
                                   "findings": snap.onchain_findings, "metadata_mutable": snap.metadata_mutable,
                                   "token_program": snap.token_program, "mayhem": snap.mayhem,
                                   "progress": snap.bonding_progress_pct, "v_sol": snap.v_sol_in_curve,
                                   "bonding_curve": snap.bonding_curve})
        try:
            show("wallet dei primi acquirenti", await svc.analyze_wallets(snap, max_new=6))
        except Exception as e:
            print("wallet: ERRORE", type(e).__name__, e)
        holders = [b["wallet"] for b in early_buyers(st, time.time()) if b["net_tokens"] > 0][:3]
        jup = JupiterCollector("https://lite-api.jup.ag", rps=0.5)
        try:
            price = f.get("price") or 1e-8
            res = await simulate_holder_sell(jup, pool, st.mint, int(0.02 / price * 1e6), holders)
            print(f"\nvendita simulata di un holder reale: {res}")
        except Exception as e:
            print("vendita simulata: ERRORE", type(e).__name__, e)
        await jup.close()
    show("costi di rete misurati", await network_costs.measure(pool))
    show("pool RPC", pool.health())
    await pool.close()


asyncio.run(main())
