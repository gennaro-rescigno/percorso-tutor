import { usePoll } from "../api";
import { TimeLine } from "../components/charts";
import { ErrorBox, Kpi, Status } from "../components/ui";
import { fmtEur, fmtNum, fmtPct, fmtPctPlain, fmtSol, fmtTime, signClass } from "../format";

export default function Overview() {
  const { data, error } = usePoll<any>("/overview", 20000);
  const s = data?.summary;
  const w = data?.worker ?? {};
  const eur = (x?: number | null) => (x != null && s?.sol_eur ? fmtEur(x * s.sol_eur) : undefined);
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Overview</h1>
      <ErrorBox error={error} />
      {s && s.total_trades < 30 && (
        <div className="warn-box">
          Campione di operazioni ancora piccolo ({s.total_trades} chiuse): win rate e profit factor non sono ancora
          statisticamente significativi.
        </div>
      )}
      <div className="grid kpis">
        <Kpi label="Capitale iniziale" value={fmtSol(s?.initial_capital_sol, 2)} sub={eur(s?.initial_capital_sol)} />
        <Kpi label="Capitale attuale" value={fmtSol(s?.equity_sol)} sub={eur(s?.equity_sol)} />
        <Kpi label="Profitto netto" value={fmtSol(s?.net_profit_sol)} tone={signClass(s?.net_profit_sol)} sub={eur(s?.net_profit_sol)} />
        <Kpi label="ROI" value={fmtPct(s?.roi)} tone={signClass(s?.roi)} />
        <Kpi label="Drawdown" value={fmtPctPlain(s?.drawdown)} sub={`max ${fmtPctPlain(s?.max_drawdown)}`} />
        <Kpi label="Win rate" value={fmtPctPlain(s?.win_rate)} sub={`PF ${s?.profit_factor ? fmtNum(s.profit_factor, 2) : "n/d"}`} />
        <Kpi label="Operazioni totali" value={fmtNum(s?.total_trades)} />
        <Kpi label="Posizioni aperte" value={fmtNum(s?.open_positions)} />
        <Kpi label="Saldo disponibile" value={fmtSol(s?.cash_sol)} sub={eur(s?.cash_sol)} />
        <Kpi label="Capitale investito" value={fmtSol(s?.invested_sol)} />
      </div>
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Equity (SOL)</h2>
          <TimeLine data={data?.equity_curve ?? []} x="ts" y="equity" name="Equity" fmt={(v) => v.toFixed(3)} area />
          <div className="note">Valore delle posizioni al prezzo di mercato corrente (non al valore di liquidazione).</div>
        </div>
        <div className="card">
          <h2>Stato del sistema</h2>
          <table>
            <tbody>
              <tr><td>Worker</td><td>{w.worker_alive ? <Status level="good" label="attivo" /> : <Status level="critical" label="non raggiungibile" />}</td></tr>
              <tr><td>Ultimo ciclo scanner</td><td>{fmtTime(w.last_cycle)}</td></tr>
              <tr><td>Token monitorati / registrati</td><td>{fmtNum(w.tracked)} / {fmtNum(data?.tokens_recorded)}</td></tr>
              <tr><td>PumpPortal (tempo reale)</td><td>{w.pumpportal_connected ? "connesso" : "non connesso"}</td></tr>
              <tr><td>Telegram</td><td>
                {!w.telegram_enabled ? "non configurato"
                  : w.telegram_failed ? <Status level="critical" label={`${w.telegram_failed} non consegnati: ${w.telegram_last_error ?? ""}`} />
                  : <Status level="good" label={`attivo · ${w.telegram_sent ?? 0} messaggi inviati nell'ultima esecuzione`} />}
              </td></tr>
              <tr><td>Mercato</td><td>{w.market_state ?? "n/d"}</td></tr>
              {Object.entries(w.sources ?? {}).map(([k, v]: any) => (
                <tr key={k}><td>Fonte: {k}</td><td>{v.ok ? <Status level="good" label="ok" /> : <Status level="critical" label={(v.error ?? "errore").slice(0, 60)} />}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
