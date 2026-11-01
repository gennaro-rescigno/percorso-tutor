"""Command line interface: ``mci <command>``.

  init-db           create tables
  worker            run the 24/7 worker (scanner + paper trading + Telegram)
  api               run the dashboard API (serves the built frontend too)
  check-sources     verify that every free data source answers from this machine
  telegram-test     send a test message to the configured chats
  fetch-history     download OHLCV for every recorded token (incl. dead ones)
  backtest          run a backtest on recorded data or a dataset file
  compare-profiles  same strategy with conservative / moderate / aggressive risk
  walkforward       walk-forward optimisation of one strategy
  stress-test       risk-management stress test on SYNTHETIC rug scenarios
  import-universe   historical survivorship-free dataset from Dune (free) + GeckoTerminal
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mci.config import get_settings


def _setup_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _parse_date(s: str | None, default: datetime) -> datetime:
    if not s:
        return default
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ----------------------------------------------------------------------------- commands
def cmd_init_db(_: argparse.Namespace) -> int:
    from mci.database.session import init_engine

    init_engine(get_settings().database_url)
    print("database pronto")
    return 0


def cmd_worker(_: argparse.Namespace) -> int:
    from mci.worker import Worker

    asyncio.run(Worker().run())
    return 0


def cmd_api(args: argparse.Namespace) -> int:
    import uvicorn

    s = get_settings()
    uvicorn.run("mci.api.app:create_app", factory=True, host=args.host or s.api_host, port=args.port or s.api_port,
                proxy_headers=True, forwarded_allow_ips="*")
    return 0


async def _check_sources() -> list[tuple[str, bool, str]]:
    from mci.collectors.dexscreener import DexScreenerCollector
    from mci.collectors.fx import SolPriceFeed
    from mci.collectors.geckoterminal import GeckoTerminalCollector
    from mci.collectors.jupiter import JupiterCollector
    from mci.collectors.rugcheck import RugCheckCollector
    from mci.collectors.solana_rpc import SolanaRpc
    from mci.domain import SOL_MINT

    s = get_settings()
    bonk = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    out: list[tuple[str, bool, str]] = []

    async def probe(name, coro, describe):
        try:
            res = await coro
            if res is None:
                out.append((name, False, "nessun dato restituito"))
                return
            out.append((name, True, describe(res)))
        except Exception as e:  # report everything, never crash
            out.append((name, False, f"{type(e).__name__}: {e}"))

    dex = DexScreenerCollector(s.dexscreener_base_url)
    gecko = GeckoTerminalCollector(s.geckoterminal_base_url)
    jup = JupiterCollector(s.jupiter_base_url, s.jupiter_api_key.get_secret_value())
    rug = RugCheckCollector(s.rugcheck_base_url)
    rpc = SolanaRpc(s.solana_rpc_url)
    fx = SolPriceFeed(s.coingecko_base_url, s.kraken_base_url)
    await probe("dexscreener profiles", dex.latest_profiles(), lambda r: f"{len(r)} profili")
    await probe("dexscreener pairs", dex.pairs_for_tokens("solana", [bonk]), lambda r: f"{len(r)} pair BONK")
    await probe("geckoterminal new_pools", gecko.new_pools(), lambda r: f"{len(r)} pool")
    await probe("jupiter price", jup.prices([SOL_MINT, bonk]), lambda r: f"{len(r)} prezzi")
    await probe("jupiter quote", jup.buy_quote(bonk, 0.1), lambda q: f"impatto {q.price_impact_pct:.4%}" if q else "nessuna rotta")
    await probe("rugcheck report", rug.report(bonk), lambda r: "ok" if r else "vuoto")
    await probe("solana rpc", rpc.mint_info(bonk), lambda r: f"decimali {r.get('decimals') if r else '?'}")
    await probe("sol price (EUR)", fx.get(), lambda p: f"{p.eur} EUR via {p.source}" if p else "non disponibile")
    for c in (dex, gecko, jup, rug, rpc, fx):
        await c.close()
    return out


def cmd_check_sources(_: argparse.Namespace) -> int:
    rows = asyncio.run(_check_sources())
    width = max(len(r[0]) for r in rows)
    for name, ok, detail in rows:
        print(f"{name:<{width}}  {'OK ' if ok else 'KO '}  {detail}")
    return 0 if all(r[1] for r in rows) else 1


def cmd_telegram_test(_: argparse.Namespace) -> int:
    from mci.telegram.client import TelegramClient

    s = get_settings()
    c = TelegramClient(s.telegram_bot_token.get_secret_value(), s.allowed_chat_ids)
    if not c.enabled:
        print("Telegram non configurato (MCI_TELEGRAM_BOT_TOKEN / MCI_TELEGRAM_CHAT_IDS)")
        return 1
    ok = asyncio.run(c.send("✅ Test Memecoin Intelligence: il bot è configurato correttamente. 🧪 PAPER TRADING"))
    msg = f"Test Telegram: inviato a {len(s.allowed_chat_ids)} chat" if ok else f"Test Telegram: invio fallito ({c.last_error})"
    print(msg)
    try:  # also record the outcome in the published activity log
        from mci.database import repo
        from mci.database.session import init_engine, session_scope

        init_engine(s.database_url)
        with session_scope() as sess:
            repo.log_event(sess, "system", msg, level="info" if ok else "error")
    except Exception:
        pass
    return 0 if ok else 1


def cmd_fetch_history(args: argparse.Namespace) -> int:
    from mci.backtesting.datasource import fetch_candles_for_universe
    from mci.collectors.geckoterminal import GeckoTerminalCollector
    from mci.database.session import init_engine

    s = get_settings()
    init_engine(s.database_url)
    now = datetime.now(timezone.utc)
    start = _parse_date(args.start, now - timedelta(days=30))
    end = _parse_date(args.end, now)
    gecko = GeckoTerminalCollector(s.geckoterminal_base_url, s.geckoterminal_calls_per_minute)
    stats = asyncio.run(fetch_candles_for_universe(gecko, start, end, args.timeframe, args.max_tokens))
    print(json.dumps(stats))
    return 0


def cmd_import_universe(args: argparse.Namespace) -> int:
    """Survivorship-free historical dataset: Dune launches (CSV or API) + GeckoTerminal OHLCV."""
    from mci.backtesting.data import save_dataset
    from mci.backtesting.universe import build_universe_dataset, launches_from_csv, launches_from_dune
    from mci.collectors.geckoterminal import GeckoTerminalCollector

    s = get_settings()
    if args.csv:
        launches = launches_from_csv(args.csv)
        origin = f"CSV {Path(args.csv).name}"
    elif args.dune_query_id:
        launches = asyncio.run(launches_from_dune(args.dune_query_id, s.dune_api_key.get_secret_value()))
        origin = f"query Dune {args.dune_query_id}"
    else:
        print("specifica --csv FILE oppure --dune-query-id ID")
        return 2
    if not launches:
        print("nessun lancio letto: controlla che il risultato abbia le colonne 'mint' e 'created_at'")
        return 1
    first = min(x.created_at for x in launches)
    last = max(x.created_at for x in launches)
    print(f"{len(launches)} lanci letti da {origin} ({first:%Y-%m-%d} -> {last:%Y-%m-%d}); "
          f"campione {min(args.sample, len(launches))}. Rate limit gratuito: può richiedere alcune ore.")
    gecko = GeckoTerminalCollector(s.geckoterminal_base_url, s.geckoterminal_calls_per_minute)

    def progress(i, n, ok):
        print(f"  {i}/{n} token elaborati, {ok} con dati", flush=True)

    ds = asyncio.run(build_universe_dataset(
        launches, gecko, sample=args.sample, seed=args.seed, timeframe=args.timeframe, hours=args.hours,
        description=f"campione casuale di lanci Pump.fun ({origin}, {first:%Y-%m-%d} -> {last:%Y-%m-%d})",
        progress=progress))
    out = args.out or str(Path(s.data_dir) / f"universe_{datetime.now(timezone.utc):%Y%m%d_%H%M}.json")
    save_dataset(ds, out)
    print("\n".join(["", f"dataset salvato: {out}", *ds.info.notes,
                     f"privo di survivorship bias: {'sì' if ds.info.survivorship_free else 'NO'}",
                     f"prossimo passo: mci compare-profiles --dataset {out} --strategies A,B,C"]))
    return 0 if ds.series else 1


def cmd_run_once(args: argparse.Namespace) -> int:
    """Windowed run (scheduled hosts such as GitHub Actions): run all loops for N seconds, then exit."""
    from mci.worker import Worker

    asyncio.run(Worker().run_window(args.window))
    return 0


def cmd_state_export(args: argparse.Namespace) -> int:
    from mci.database.session import init_engine
    from mci.state_io import export_state

    init_engine(get_settings().database_url)
    print(json.dumps(export_state(args.out)))
    return 0


def cmd_state_import(args: argparse.Namespace) -> int:
    from mci.database.session import init_engine
    from mci.state_io import import_state

    init_engine(get_settings().database_url)
    if not Path(args.file).exists():
        print("nessun file di stato da importare")
        return 0
    print(json.dumps(import_state(args.file)))
    return 0


def cmd_export_static(args: argparse.Namespace) -> int:
    from mci.state_io import export_static

    print(f"{export_static(args.out)} file JSON scritti in {args.out}")
    return 0


def cmd_publish_static(args: argparse.Namespace) -> int:
    """Server mode: keep a read-only public copy of the dashboard fresh (same data the GitHub Pages dashboard
    published: paper trading and public token data, secrets scrubbed). The data folder is swapped atomically."""
    import shutil
    import tempfile
    import time

    from mci.state_io import export_static

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    site = Path(args.site)
    if site.is_dir():
        for item in site.iterdir():
            if item.is_dir():
                shutil.copytree(item, out / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, out / item.name)
    while True:
        try:
            tmp = Path(tempfile.mkdtemp(dir=out, prefix=".data-"))
            export_static(tmp)
            tmp.chmod(0o755)
            live = out / "data"
            if live.exists():
                live.rename(out / f".old-{time.time_ns()}")
            tmp.rename(live)
        except Exception:
            logging.getLogger(__name__).exception("publish-static failed")
        finally:
            from mci.database.session import get_engine

            get_engine().dispose()  # export_static builds a fresh app/engine each round: close its connections
        for stale in list(out.glob(".old-*")) + [d for d in out.glob(".data-*") if d.is_dir()]:
            shutil.rmtree(stale, ignore_errors=True)
        if args.once:
            return 0
        time.sleep(args.every)


def _load_dataset(args: argparse.Namespace):
    from mci.backtesting.data import load_dataset
    from mci.backtesting.datasource import dataset_from_db
    from mci.database.session import init_engine

    if args.dataset:
        return load_dataset(args.dataset)
    init_engine(get_settings().database_url)
    now = datetime.now(timezone.utc)
    return dataset_from_db(_parse_date(args.start, now - timedelta(days=90)), _parse_date(args.end, now), args.timeframe)


def _store_run(name: str, res, report_md: str) -> None:
    from mci.database.models import BacktestRun
    from mci.database.session import init_engine, session_scope

    init_engine(get_settings().database_url)
    d = res.to_dict()
    with session_scope() as s:
        s.add(BacktestRun(name=name, status="done", config=d["config"], metrics=d["metrics"],
                          equity_curve=d["equity_curve"], trades=d["trades"], data_info=d["data_info"],
                          warnings=d["warnings"], report_md=report_md))


def cmd_backtest(args: argparse.Namespace) -> int:
    from mci.backtesting.engine import BacktestConfig, run_backtest
    from mci.backtesting.report import render_report

    ds = _load_dataset(args)
    cfg = BacktestConfig(strategy_codes=args.strategies.split(","), profile=args.profile, exit_policy=args.exit,
                         initial_capital_sol=args.capital, seed=args.seed)
    res = run_backtest(ds, cfg)
    name = f"{args.strategies} {args.profile} {args.exit}"
    md = render_report(f"Backtest {name}", {name: res})
    _write(args.out, md)
    _store_run(name, res, md)
    print(md)
    return 0


def cmd_compare_profiles(args: argparse.Namespace) -> int:
    from mci.backtesting.engine import BacktestConfig, run_backtest
    from mci.backtesting.report import render_report

    ds = _load_dataset(args)
    results = {}
    for prof in ("conservative", "moderate", "aggressive"):
        cfg = BacktestConfig(strategy_codes=args.strategies.split(","), profile=prof, exit_policy=args.exit,
                             initial_capital_sol=args.capital, seed=args.seed)
        results[prof] = run_backtest(ds, cfg)
    md = render_report(f"Confronto profili di rischio – strategie {args.strategies}", results)
    _write(args.out, md)
    print(md)
    return 0


def cmd_walkforward(args: argparse.Namespace) -> int:
    from mci.backtesting.engine import BacktestConfig
    from mci.backtesting.walkforward import walk_forward

    ds = _load_dataset(args)
    grid = json.loads(args.grid)
    base = BacktestConfig(strategy_codes=[args.strategy], profile=args.profile, exit_policy=args.exit,
                          initial_capital_sol=args.capital)
    rep = walk_forward(ds, base, args.strategy, grid, n_windows=args.windows, min_trades=args.min_trades)
    lines = [f"# Walk-forward strategia {args.strategy}", "", f"Trade out-of-sample: {rep.oos_trades}",
             f"P/L out-of-sample: {rep.oos_pnl_sol:.4f} SOL", ""]
    for i, w in enumerate(rep.windows, 1):
        m = w.test_result.metrics
        lines.append(f"- Finestra {i}: parametri {w.chosen_params} → test: {m.n_trades} trade, "
                     f"rendimento {m.return_pct:.2%}, max DD {m.max_drawdown_pct:.2%}")
    lines += [f"- Nota: {n}" for n in rep.notes]
    md = "\n".join(lines)
    _write(args.out, md)
    print(md)
    return 0


def cmd_stress_test(args: argparse.Namespace) -> int:
    from mci.backtesting.engine import BacktestConfig, run_backtest
    from mci.backtesting.report import render_report
    from mci.backtesting.synthetic import scenario_dataset

    ds = scenario_dataset(["rug"] * args.rugs + ["pnd", "dead", "noise"], seed=args.seed)
    results = {}
    for prof in ("conservative", "moderate", "aggressive"):
        cfg = BacktestConfig(strategy_codes=["A"], profile=prof, initial_capital_sol=2.0, seed=args.seed,
                             p_fail_entry=0.0, p_fail_exit=0.05)
        results[prof] = run_backtest(ds, cfg)
    md = render_report("Stress test del risk management (scenari sintetici di rug pull)", results)
    _write(args.out, md)
    print(md)
    return 0


def _write(path: str | None, text: str) -> None:
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text)


def main(argv: list[str] | None = None) -> int:
    s = get_settings()
    _setup_logging(s.log_level)
    p = argparse.ArgumentParser(prog="mci", description="Memecoin Intelligence & Trading System")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db").set_defaults(fn=cmd_init_db)
    sub.add_parser("worker").set_defaults(fn=cmd_worker)
    a = sub.add_parser("api")
    a.add_argument("--host")
    a.add_argument("--port", type=int)
    a.set_defaults(fn=cmd_api)
    sub.add_parser("check-sources").set_defaults(fn=cmd_check_sources)
    sub.add_parser("telegram-test").set_defaults(fn=cmd_telegram_test)
    f = sub.add_parser("fetch-history")
    f.add_argument("--start")
    f.add_argument("--end")
    f.add_argument("--timeframe", default="1m")
    f.add_argument("--max-tokens", type=int, default=2000)
    f.set_defaults(fn=cmd_fetch_history)

    ro = sub.add_parser("run-once", help="esegue tutti i cicli per N secondi e termina (GitHub Actions)")
    ro.add_argument("--window", type=int, default=240)
    ro.set_defaults(fn=cmd_run_once)
    se = sub.add_parser("state-export")
    se.add_argument("--out", required=True)
    se.set_defaults(fn=cmd_state_export)
    si = sub.add_parser("state-import")
    si.add_argument("--file", required=True)
    si.set_defaults(fn=cmd_state_import)
    ps = sub.add_parser("publish-static", help="server: aggiorna di continuo la dashboard pubblica in sola lettura")
    ps.add_argument("--out", required=True)
    ps.add_argument("--site", default="/app/frontend/static-dist", help="frontend statico già compilato")
    ps.add_argument("--every", type=int, default=60)
    ps.add_argument("--once", action="store_true")
    ps.set_defaults(fn=cmd_publish_static)
    es = sub.add_parser("export-static", help="dati JSON per la dashboard statica in sola lettura")
    es.add_argument("--out", required=True)
    es.set_defaults(fn=cmd_export_static)

    iu = sub.add_parser("import-universe", help="dataset storico senza survivorship bias da Dune + GeckoTerminal")
    iu.add_argument("--csv", help="file CSV esportato da Dune (colonne mint, created_at)")
    iu.add_argument("--dune-query-id", type=int, help="ID della query Dune (richiede MCI_DUNE_API_KEY)")
    iu.add_argument("--sample", type=int, default=500)
    iu.add_argument("--hours", type=int, default=24, help="ore di storico dopo il lancio per ogni token")
    iu.add_argument("--timeframe", default="1m")
    iu.add_argument("--seed", type=int, default=7)
    iu.add_argument("--out")
    iu.set_defaults(fn=cmd_import_universe)

    def common(sp):
        sp.add_argument("--dataset", help="file JSON del dataset (altrimenti dati registrati nel DB)")
        sp.add_argument("--start")
        sp.add_argument("--end")
        sp.add_argument("--timeframe", default="1m")
        sp.add_argument("--profile", default="moderate")
        sp.add_argument("--exit", default="ladder_trailing")
        sp.add_argument("--capital", type=float, default=2.0)
        sp.add_argument("--seed", type=int, default=42)
        sp.add_argument("--out")

    b = sub.add_parser("backtest")
    common(b)
    b.add_argument("--strategies", default="A,B,C,D,E")
    b.set_defaults(fn=cmd_backtest)
    c = sub.add_parser("compare-profiles")
    common(c)
    c.add_argument("--strategies", default="A,B,C,D,E")
    c.set_defaults(fn=cmd_compare_profiles)
    w = sub.add_parser("walkforward")
    common(w)
    w.add_argument("--strategy", required=True)
    w.add_argument("--grid", required=True, help='es. \'{"vol_mult":[1.5,2.0,2.5]}\'')
    w.add_argument("--windows", type=int, default=4)
    w.add_argument("--min-trades", type=int, default=20)
    w.set_defaults(fn=cmd_walkforward)
    st = sub.add_parser("stress-test")
    st.add_argument("--rugs", type=int, default=8)
    st.add_argument("--seed", type=int, default=3)
    st.add_argument("--out")
    st.set_defaults(fn=cmd_stress_test)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
