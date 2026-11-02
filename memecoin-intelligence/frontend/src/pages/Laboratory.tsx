import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePoll } from "../api";
import { TimeLine } from "../components/charts";
import { Column, DataTable, ErrorBox, Kpi } from "../components/ui";
import { fmtEur, fmtNum, fmtPct, fmtPctPlain, fmtPrice, fmtSol, fmtTime, signClass } from "../format";

const STRATEGY_NAMES: Record<string, string> = {
  A: "A · Early Entry", B: "B · Momentum", C: "C · Pullback", D: "D · Accumulazione", E: "E · Revival",
};
const strategyName = (k: string) => STRATEGY_NAMES[k] ?? k;
const minutes = (m?: number | null) =>
  m == null ? "n/d" : m >= 120 ? `${fmtNum(m / 60, 1)} h` : `${Math.round(m)} min`;

const strategyCols: Column<any>[] = [
  { key: "strategy", label: "Strategia", render: (r) => <b>{strategyName(r.strategy)}</b> },
  { key: "trades", label: "Chiuse", num: true },
  { key: "open", label: "Aperte", num: true },
  { key: "wins", label: "Vinte", num: true },
  { key: "losses", label: "Perse", num: true },
  { key: "win_rate", label: "Win rate", num: true, render: (r) => fmtPctPlain(r.win_rate) },
  { key: "pnl_sol", label: "Profitto/perdita", num: true, render: (r) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
  { key: "avg_return", label: "Media per operazione", num: true, render: (r) => <span className={signClass(r.avg_return)}>{fmtPct(r.avg_return)}</span> },
  { key: "best_return", label: "Migliore", num: true, render: (r) => fmtPct(r.best_return) },
  { key: "worst_return", label: "Peggiore", num: true, render: (r) => fmtPct(r.worst_return) },
  { key: "profit_factor", label: "Profit factor", num: true, render: (r) => (r.profit_factor == null ? "n/d" : fmtNum(r.profit_factor, 2)) },
  { key: "avg_hold_min", label: "Durata media", num: true, render: (r) => minutes(r.avg_hold_min) },
];

export default function Laboratory() {
  const { data, error } = usePoll<any>("/lab", 30000);
  const [status, setStatus] = useState("all");
  const nav = useNavigate();
  const s = data?.summary;
  const eur = (x?: number | null) => (x != null && s?.sol_eur ? fmtEur(x * s.sol_eur) : undefined);
  const positions = (data?.positions ?? []).filter((p: any) => status === "all" || p.status === status);
  const skipped = Object.entries(data?.skipped ?? {}) as [string, number][];
  const posCols: Column<any>[] = [
    { key: "symbol", label: "Token", render: (r) => <b>{r.symbol}</b> },
    { key: "strategy", label: "Strategia", render: (r) => strategyName(r.strategy) },
    { key: "status", label: "Stato", render: (r) => (r.status === "open" ? "aperta" : "chiusa") },
    { key: "opened_at", label: "Apertura", render: (r) => fmtTime(r.opened_at) },
    { key: "closed_at", label: "Chiusura", render: (r) => (r.closed_at ? fmtTime(r.closed_at) : "—") },
    { key: "entry_price", label: "Ingresso", num: true, render: (r) => fmtPrice(r.entry_price) },
    { key: "stake_sol", label: "Puntata", num: true, render: (r) => fmtSol(r.stake_sol) },
    { key: "pnl_sol", label: "Profitto/perdita", num: true, render: (r) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
    { key: "return_pct", label: "Rendimento", num: true, render: (r) => <span className={signClass(r.return_pct)}>{fmtPct(r.return_pct)}</span> },
    { key: "duration_min", label: "Durata", num: true, render: (r) => minutes(r.duration_min) },
    { key: "exit_reason", label: "Motivo uscita", render: (r) => <span className="muted">{r.exit_reason ?? ""}</span> },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Laboratorio – strategie senza limiti</h1>
      <ErrorBox error={error} />
      <div className="warn-box">
        Portafoglio <b>virtuale</b>, separato da quello principale: prende <b>ogni</b> segnale delle strategie, senza i limiti
        di rischio (posizioni massime, operazioni al giorno, pausa dopo un'uscita, score minimo, stop giornalieri). Stessi
        token, stessi prezzi e stesse regole di uscita; costi stimati con il modello del pool (commissioni, impatto,
        slittamento). Non invia messaggi Telegram e non usa soldi veri. Serve a capire come si comporta ogni strategia da sola.
        {data?.started_at && <> Attivo dal {fmtTime(data.started_at)}.</>}
      </div>
      <div className="card section">
        <b>Stato del Laboratorio:</b>{" "}
        {data?.last_scan_at ? <>ultimo controllo dei segnali {fmtTime(data.last_scan_at)}</> : "in avvio"}
        {" · "}
        {data?.stats?.signals
          ? <>segnali ricevuti finora: <b>{fmtNum(data.stats.signals)}</b> (ultimo: {data.stats.last_signal}, {fmtTime(data.stats.last_signal_at)}){" · "}
              per strategia: {Object.entries(data.stats.by_strategy ?? {}).map(([k, v]) => `${k} ${v}`).join(", ")}</>
          : "nessun segnale ancora: da quando il Laboratorio è partito nessuna strategia ha visto un punto d'ingresso"}
      </div>
      {s && s.total_trades < 30 && (
        <div className="warn-box">
          Operazioni chiuse finora: {s.total_trades}. Sotto le 30 operazioni win rate e medie non sono ancora affidabili.
        </div>
      )}
      <div className="grid kpis">
        <Kpi label="Capitale iniziale" value={fmtSol(s?.initial_capital_sol, 2)} sub={eur(s?.initial_capital_sol)} />
        <Kpi label="Saldo virtuale" value={fmtSol(s?.equity_sol)} sub={eur(s?.equity_sol)} />
        <Kpi label="Profitto/perdita" value={fmtSol(s?.net_profit_sol)} tone={signClass(s?.net_profit_sol)} sub={eur(s?.net_profit_sol)} />
        <Kpi label="ROI" value={fmtPct(s?.roi)} tone={signClass(s?.roi)} />
        <Kpi label="Operazioni chiuse" value={fmtNum(s?.total_trades)} sub={`aperte ${fmtNum(s?.open_positions)}`} />
        <Kpi label="Win rate" value={fmtPctPlain(s?.win_rate)} sub={`PF ${s?.profit_factor ? fmtNum(s.profit_factor, 2) : "n/d"}`} />
        <Kpi label="Drawdown massimo" value={fmtPctPlain(s?.max_drawdown)} />
        <Kpi label="Commissioni + slippage" value={fmtSol((s?.fees_sol ?? 0) + (s?.slippage_sol ?? 0))} />
      </div>
      <div className="card section">
        <h2>Come si muove il saldo (SOL)</h2>
        <TimeLine data={data?.equity_curve ?? []} x="ts" y="equity" name="Saldo virtuale" fmt={(v) => v.toFixed(4)} area />
        <div className="note">Aggiornato ogni 5 minuti; le posizioni aperte sono valutate al prezzo di mercato.</div>
      </div>
      <div className="card section">
        <h2>Risultati per strategia – Laboratorio (senza limiti)</h2>
        <DataTable rows={data?.by_strategy ?? []} columns={strategyCols} empty="Ancora nessuna operazione nel Laboratorio" />
      </div>
      <div className="card section">
        <h2>Confronto: portafoglio principale (con limiti)</h2>
        <DataTable rows={data?.main_by_strategy ?? []} columns={strategyCols} empty="Nessuna operazione" />
      </div>
      {skipped.length > 0 && (
        <div className="card section">
          <h2>Segnali non simulabili</h2>
          <table>
            <tbody>
              {skipped.map(([reason, n]) => (
                <tr key={reason}><td>{reason}</td><td className="num">{fmtNum(n)}</td></tr>
              ))}
            </tbody>
          </table>
          <div className="note">Restano solo vincoli fisici (capitale virtuale esaurito, liquidità sconosciuta, impatto di prezzo troppo alto), non regole di rischio.</div>
        </div>
      )}
      <div className="card section">
        <h2>Tutte le operazioni del Laboratorio</h2>
        <div className="tabs">
          {[["all", "Tutte"], ["open", "Aperte"], ["closed", "Chiuse"]].map(([k, l]) => (
            <button key={k} className={status === k ? "active" : ""} onClick={() => setStatus(k)}>{l}</button>
          ))}
        </div>
        <DataTable rows={positions} columns={posCols} onRowClick={(r) => nav(`/token/${r.token}`)}
                   initialSort={{ key: "opened_at", desc: true }} empty="Nessuna operazione" />
      </div>
    </>
  );
}
