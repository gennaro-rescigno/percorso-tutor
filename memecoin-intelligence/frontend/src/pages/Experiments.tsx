import { useNavigate } from "react-router-dom";
import { usePoll } from "../api";
import { TimeLine } from "../components/charts";
import { Column, DataTable, ErrorBox, Kpi, Status } from "../components/ui";
import { fmtNum, fmtPct, fmtPctPlain, fmtSol, fmtTime, signClass } from "../format";

const STRAT: Record<string, string> = {
  A: "A · Early Entry", B: "B · Momentum", C: "C · Pullback", D: "D · Accumulazione", E: "E · Revival",
  O: "O · Curva organica",
};

const stratCols: Column<any>[] = [
  { key: "strategy", label: "Strategia", render: (r) => <b>{STRAT[r.strategy] ?? r.strategy}</b> },
  { key: "trades", label: "Chiuse", num: true },
  { key: "open", label: "Aperte", num: true },
  { key: "win_rate", label: "Win rate", num: true, render: (r) => fmtPctPlain(r.win_rate) },
  { key: "pnl_sol", label: "Profitto/perdita", num: true, render: (r) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
  { key: "avg_return", label: "Media per operazione", num: true, render: (r) => <span className={signClass(r.avg_return)}>{fmtPct(r.avg_return)}</span> },
];

function Experiment({ e }: { e: any }) {
  const nav = useNavigate();
  const s = e.summary ?? {};
  const g = e.gate ?? {};
  const skipped = Object.entries(e.skipped ?? {}) as [string, number][];
  const posCols: Column<any>[] = [
    { key: "symbol", label: "Token", render: (r) => <b>{r.symbol}</b> },
    { key: "status", label: "Stato", render: (r) => (r.status === "open" ? "aperta" : "chiusa") },
    { key: "opened_at", label: "Apertura", render: (r) => fmtTime(r.opened_at) },
    { key: "return_pct", label: "Rendimento", num: true, render: (r) => <span className={signClass(r.return_pct)}>{fmtPct(r.return_pct)}</span> },
    { key: "exit_reason", label: "Motivo uscita", render: (r) => <span className="muted">{r.exit_reason ?? ""}</span> },
  ];
  return (
    <div className="card section">
      <h2>{e.title} <span className="muted mono">({e.mode})</span></h2>
      <div className="note"><b>Ipotesi:</b> {e.hypothesis}. Attivo dal {fmtTime(e.started_at)}
        {e.last_scan_at ? <> · ultimo controllo {fmtTime(e.last_scan_at)}</> : null}
        {" · "}segnali: {fmtNum(e.stats?.signals ?? 0)}</div>
      <div className="grid kpis" style={{ marginTop: 10 }}>
        <Kpi label="Saldo virtuale" value={fmtSol(s.equity_sol)} />
        <Kpi label="Profitto/perdita" value={fmtSol(s.net_profit_sol)} tone={signClass(s.net_profit_sol)} />
        <Kpi label="ROI" value={fmtPct(s.roi)} tone={signClass(s.roi)} />
        <Kpi label="Operazioni chiuse" value={fmtNum(s.total_trades)} sub={`aperte ${fmtNum(s.open_positions)}`} />
        <Kpi label="Win rate" value={fmtPctPlain(s.win_rate)} />
        <Kpi label="Rendimento medio (IC 95%)" value={fmtPct(g.experiment?.mean_return)}
             sub={g.experiment?.ci95 ? `${fmtPct(g.experiment.ci95[0])} … ${fmtPct(g.experiment.ci95[1])}` : "campione troppo piccolo"} />
      </div>
      <h3>Cancello di promozione</h3>
      <table><tbody>
        {(g.checks ?? []).map((c: any) => (
          <tr key={c.check}>
            <td><Status level={c.ok ? "good" : "warning"} label={c.ok ? "superato" : "non ancora"} /></td>
            <td>{c.check}</td>
            <td className="num muted">{c.value == null ? "" : Array.isArray(c.value) ? c.value.map((v: number) => fmtPct(v)).join(" … ") : String(c.value)}</td>
          </tr>
        ))}
      </tbody></table>
      <div className={g.promotable ? "warn-box" : "note"} style={{ marginTop: 8 }}><b>{g.status}</b></div>
      <div className="grid cols-2" style={{ marginTop: 10 }}>
        <div>
          <h3>Saldo virtuale (SOL)</h3>
          <TimeLine data={e.equity_curve ?? []} x="ts" y="equity" name="Saldo" fmt={(v) => v.toFixed(4)} area />
        </div>
        <div>
          <h3>Per strategia</h3>
          <DataTable rows={e.by_strategy ?? []} columns={stratCols} empty="Ancora nessuna operazione" />
          {skipped.length > 0 && (
            <>
              <h3>Segnali scartati dall'esperimento</h3>
              <table><tbody>{skipped.map(([k, v]) => <tr key={k}><td>{k}</td><td className="num">{fmtNum(v)}</td></tr>)}</tbody></table>
            </>
          )}
        </div>
      </div>
      <h3>Operazioni</h3>
      <DataTable rows={e.positions ?? []} columns={posCols} onRowClick={(r) => nav(`/token/${r.token}`)}
                 initialSort={{ key: "opened_at", desc: true }} empty="Nessuna operazione" />
    </div>
  );
}

export default function Experiments() {
  const { data, error } = usePoll<any>("/experiments", 60000);
  const b = data?.baseline?.summary;
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Esperimenti (shadow)</h1>
      <ErrorBox error={error} />
      <div className="warn-box">
        Ogni esperimento è un portafoglio <b>virtuale</b> separato che prova <b>una</b> modifica (nuove regole o una nuova
        strategia) senza toccare il portafoglio principale. I parametri sono fissati in anticipo; un esperimento diventa
        "promuovibile" solo se supera tutti i controlli statistici fuori campione, e anche allora <b>il bot non lo attiva
        da solo</b>: serve la tua approvazione esplicita.
      </div>
      {b && (
        <div className="card section">
          <b>Riferimento – Laboratorio:</b> {fmtNum(b.total_trades)} operazioni chiuse, win rate {fmtPctPlain(b.win_rate)},
          ROI <span className={signClass(b.roi)}>{fmtPct(b.roi)}</span>
        </div>
      )}
      {(data?.experiments ?? []).map((e: any) => <Experiment key={e.mode} e={e} />)}
      <div className="card section">
        <h2>Regole e loro modalità</h2>
        <table><tbody>
          {(data?.rules ?? []).map((r: any) => (
            <tr key={r.code}>
              <td><Status level={r.mode === "enforce" ? "critical" : "warning"} label={r.mode === "enforce" ? "applicata" : "shadow"} /></td>
              <td className="mono">{r.code}</td><td>{r.description}</td>
            </tr>
          ))}
        </tbody></table>
        <div className="note">"Applicata" = blocca gli acquisti in tutti i portafogli (sicurezza). "Shadow" = registra solo cosa
          avrebbe fatto; viene applicata nell'esperimento x_safe per misurarne l'effetto.</div>
      </div>
    </>
  );
}
