import { useState } from "react";
import { usePoll } from "../api";
import { Histogram, SignedBars, TimeLine } from "../components/charts";
import { Column, DataTable, ErrorBox, Kpi } from "../components/ui";
import { fmtNum, fmtPct, fmtPctPlain, fmtSol, signClass } from "../format";

export default function Performance() {
  const { data, error } = usePoll<any>("/performance", 60000);
  const [period, setPeriod] = useState<"daily" | "weekly" | "monthly">("daily");
  const s = data?.summary;
  const stratCols: Column<any>[] = [
    { key: "strategy", label: "Strategia" },
    { key: "trades", label: "Operazioni", num: true },
    { key: "pnl_sol", label: "P/L", num: true, render: (r) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
    { key: "win_rate", label: "Win rate", num: true, render: (r) => fmtPctPlain(r.win_rate) },
    { key: "profit_factor", label: "Profit factor", num: true, render: (r) => (r.profit_factor == null ? "n/d" : fmtNum(r.profit_factor, 2)) },
  ];
  const sigCols: Column<any>[] = [
    { key: "strategy", label: "Strategia" },
    { key: "signals", label: "Segnali con esito a 1h", num: true },
    { key: "avg_return_1h", label: "Rendimento medio 1h", num: true, render: (r) => fmtPct(r.avg_return_1h) },
    { key: "positive_share", label: "Quota positivi", num: true, render: (r) => fmtPctPlain(r.positive_share) },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Performance</h1>
      <ErrorBox error={error} />
      <div className="grid kpis">
        <Kpi label="Win rate" value={fmtPctPlain(s?.win_rate)} />
        <Kpi label="Profit factor" value={s?.profit_factor ? fmtNum(s.profit_factor, 2) : "n/d"} />
        <Kpi label="Expectancy / trade" value={fmtSol(s?.expectancy_sol)} tone={signClass(s?.expectancy_sol)} />
        <Kpi label="Max drawdown" value={fmtPctPlain(s?.max_drawdown)} />
        <Kpi label="Commissioni totali" value={fmtSol(s?.fees_sol)} />
        <Kpi label="Slippage totale" value={fmtSol(s?.slippage_sol)} />
      </div>
      <div className="grid cols-2 section">
        <div className="card"><h2>Equity curve (SOL)</h2>
          <TimeLine data={data?.equity_curve ?? []} x="ts" y="equity" name="Equity" fmt={(v) => v.toFixed(3)} /></div>
        <div className="card"><h2>Drawdown</h2>
          <TimeLine data={(data?.equity_curve ?? []).map((r: any) => ({ ...r, dd: -r.drawdown }))} x="ts" y="dd" name="Drawdown"
                    fmt={(v) => fmtPctPlain(v)} area color="var(--loss)" /></div>
        <div className="card">
          <h2>Profitto {period === "daily" ? "giornaliero" : period === "weekly" ? "settimanale" : "mensile"} (SOL)</h2>
          <div className="tabs">
            {(["daily", "weekly", "monthly"] as const).map((p) => (
              <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>
                {p === "daily" ? "Giorno" : p === "weekly" ? "Settimana" : "Mese"}
              </button>
            ))}
          </div>
          <SignedBars data={data?.[period] ?? []} x="period" y="pnl_sol" name="P/L" fmt={(v) => v.toFixed(4)} />
        </div>
        <div className="card"><h2>Distribuzione dei rendimenti per operazione</h2><Histogram values={data?.returns ?? []} /></div>
      </div>
      <div className="grid cols-2 section">
        <div className="card"><h2>Performance per strategia</h2><DataTable rows={data?.by_strategy ?? []} columns={stratCols} /></div>
        <div className="card"><h2>Performance per categoria (DEX/launchpad)</h2>
          <DataTable rows={data?.by_category ?? []} columns={[
            { key: "category", label: "Categoria" }, { key: "trades", label: "Operazioni", num: true },
            { key: "pnl_sol", label: "P/L", num: true, render: (r: any) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
          ]} /></div>
      </div>
      <div className="card section">
        <h2>Qualità dei segnali (cosa è successo dopo ogni segnale, anche non eseguito)</h2>
        <DataTable rows={data?.signal_quality ?? []} columns={sigCols} empty="Nessun segnale con esito ancora misurato" />
        <div className="note">Serve a capire quali strategie generano falsi segnali. Nessun parametro viene modificato automaticamente: ogni modifica va validata su dati indipendenti.</div>
      </div>
    </>
  );
}
