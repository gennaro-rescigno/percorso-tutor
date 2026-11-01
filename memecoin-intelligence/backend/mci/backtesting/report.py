"""Markdown reports for backtest results (Italian), with mandatory caveats."""

from __future__ import annotations

from mci.backtesting.engine import BacktestResult


def _f(x: float | None, fmt: str = "{:.4f}") -> str:
    if x is None:
        return "n/d"
    if x == float("inf"):
        return "∞"
    return fmt.format(x)


def _pct(x: float | None) -> str:
    return _f(None if x is None else x * 100, "{:.2f}%")


def result_table(results: dict[str, BacktestResult], sol_eur: float | None = None) -> str:
    names = list(results)
    rows = [
        ("Capitale iniziale (SOL)", lambda m: _f(m.initial_capital_sol)),
        ("Capitale finale (SOL)", lambda m: _f(m.final_capital_sol)),
        ("Profitto netto (SOL)", lambda m: _f(m.net_profit_sol)),
        ("Rendimento", lambda m: _pct(m.return_pct)),
        ("Operazioni", lambda m: str(m.n_trades)),
        ("Win rate", lambda m: _pct(m.win_rate)),
        ("Loss rate", lambda m: _pct(m.loss_rate)),
        ("Profit factor", lambda m: _f(m.profit_factor, "{:.2f}")),
        ("Expectancy / trade (SOL)", lambda m: _f(m.expectancy_sol)),
        ("Expectancy / trade (%)", lambda m: _pct(m.expectancy_pct)),
        ("IC 95% expectancy", lambda m: "n/d" if not m.expectancy_ci95_pct else f"[{m.expectancy_ci95_pct[0]:.2%}, {m.expectancy_ci95_pct[1]:.2%}]"),
        ("Average win (SOL)", lambda m: _f(m.avg_win_sol)),
        ("Average loss (SOL)", lambda m: _f(m.avg_loss_sol)),
        ("Max drawdown", lambda m: _pct(m.max_drawdown_pct)),
        ("Max DD Monte Carlo p50 / p95", lambda m: f"{_pct(m.mc_max_dd_p50)} / {_pct(m.mc_max_dd_p95)}"),
        ("Sharpe", lambda m: _f(m.sharpe, "{:.2f}")),
        ("Sortino", lambda m: _f(m.sortino, "{:.2f}")),
        ("Serie massima di perdite", lambda m: str(m.max_consecutive_losses)),
        ("Durata media (min)", lambda m: _f(m.avg_hold_minutes, "{:.0f}")),
        ("Commissioni totali (SOL)", lambda m: _f(m.total_fees_sol)),
        ("Slippage totale (SOL)", lambda m: _f(m.total_slippage_sol)),
        ("Capitale massimo investito (SOL)", lambda m: _f(m.max_capital_used_sol)),
        ("Ordini falliti", lambda m: str(m.failed_orders)),
        ("Uscite su token morti", lambda m: str(m.dead_token_exits)),
        ("Robusto?", lambda m: "SÌ" if m.robust else "NO"),
    ]
    out = ["| Metrica | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for label, fn in rows:
        out.append(f"| {label} | " + " | ".join(fn(results[n].metrics) for n in names) + " |")
    if sol_eur:
        out.append(
            "| Capitale finale (EUR, al prezzo SOL attuale) | "
            + " | ".join(f"{results[n].metrics.final_capital_sol * sol_eur:,.2f} €" for n in names) + " |"
        )
    return "\n".join(out)


def render_report(title: str, results: dict[str, BacktestResult], sol_eur: float | None = None) -> str:
    any_res = next(iter(results.values()))
    info = any_res.data_info
    lines = [f"# {title}", ""]
    if info.get("source") == "synthetic":
        lines += ["> ⚠️ **DATI SINTETICI** — questo report verifica il funzionamento del motore e del risk",
                  "> management. NON è una misura della redditività di alcuna strategia.", ""]
    lines += [
        "## Dati",
        f"- Fonte: `{info.get('source')}` — universo: {info.get('universe_method')}",
        f"- Token: {info.get('n_tokens')} — periodo: {info.get('start')} → {info.get('end')}",
        f"- Privo di survivorship bias: {'sì' if info.get('survivorship_free') else '**NO**'}",
        f"- Feature point-in-time: {'sì' if info.get('point_in_time_features') else '**NO (solo OHLCV)**'}",
    ]
    for n in info.get("notes") or []:
        lines.append(f"- Nota: {n}")
    lines += ["", "## Risultati", "", result_table(results, sol_eur), ""]
    for name, r in results.items():
        m = r.metrics
        lines += [f"### {name}", f"- Segnali generati: {r.signals}", f"- Sharpe/Sortino: {m.ratio_note}"]
        if m.robustness_notes:
            lines.append("- Robustezza: " + "; ".join(m.robustness_notes))
        if m.by_exit_reason:
            lines.append("- Motivi di uscita: " + ", ".join(f"{k}={v}" for k, v in sorted(m.by_exit_reason.items())))
        if r.rejections:
            top = sorted(r.rejections.items(), key=lambda kv: -kv[1])[:6]
            lines.append("- Segnali/ordini scartati: " + "; ".join(f"{k} ({v})" for k, v in top))
        for w in r.warnings[:5]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
    lines += [
        "## Avvertenze",
        "- Le metriche sono calcolate con commissioni, slippage, impatto AMM, latenza e transazioni fallite simulate.",
        "- Un risultato è considerato robusto solo con ≥100 trade e intervallo di confidenza dell'expectancy > 0.",
        "- Risultati passati non garantiscono risultati futuri; il regime del mercato memecoin cambia rapidamente.",
    ]
    return "\n".join(lines)
