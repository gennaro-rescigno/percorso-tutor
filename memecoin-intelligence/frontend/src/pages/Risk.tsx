import { useState } from "react";
import { READ_ONLY_MSG, STATIC, api, usePoll } from "../api";
import { HBars } from "../components/charts";
import { ErrorBox, Kpi, Status } from "../components/ui";
import { fmtPct, fmtPctPlain, fmtSol, fmtTime } from "../format";

export default function Risk() {
  const { data, error, reload } = usePoll<any>("/risk", 15000);
  const [msg, setMsg] = useState<string | null>(null);
  const p = data?.profile ?? {};
  async function act(a: string, confirmText: string) {
    if (!window.confirm(confirmText)) return;
    try {
      await api(`/control/${a}`, { method: "POST" });
      setMsg(`Comando '${a}' inviato: il worker lo applica al prossimo ciclo.`);
      reload();
    } catch (e: any) {
      setMsg(e.message);
    }
  }
  const exposure = Object.entries(data?.exposure_by_token ?? {}).map(([k, v]: any) => ({ label: k.slice(0, 8), value: v }));
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Risk Management</h1>
      <ErrorBox error={error} />
      {msg && <div className="warn-box">{msg}</div>}
      <div className="grid kpis">
        <Kpi label="Profilo" value={p.name ?? "n/d"} sub={`rischio ${fmtPctPlain(p.risk_per_trade_pct, 2)} / trade`} />
        <Kpi label="Capitale esposto" value={fmtSol(data?.exposure_sol)} sub={`${fmtPctPlain(data?.exposure_pct)} (max ${fmtPctPlain(p.max_exposure_pct, 0)})`} />
        <Kpi label="Capitale disponibile" value={fmtSol(data?.cash_sol)} sub={`riserva minima ${fmtPctPlain(p.min_cash_reserve_pct, 0)}`} />
        <Kpi label="Drawdown corrente" value={fmtPctPlain(data?.drawdown)} sub={`riduzione a ${fmtPctPlain(p.dd_reduce_threshold_pct, 0)}, stop a ${fmtPctPlain(p.max_drawdown_pause_pct, 0)}`} />
        <Kpi label="P/L di oggi" value={fmtPct(data?.daily_pnl_pct)} sub={`limite −${fmtPctPlain(data?.daily_loss_limit_pct, 0)}`} />
        <Kpi label="Posizioni" value={`${data?.open_positions ?? 0} / ${data?.max_positions ?? "n/d"}`} sub={`operazioni oggi ${data?.trades_today ?? 0} / ${p.max_trades_per_day ?? "n/d"}`} />
      </div>
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Kill switch e controlli</h2>
          <p>{data?.kill_switch ? <Status level="critical" label={`ATTIVO – ${data.kill_reason}`} /> : <Status level="good" label="non attivo" />}{" "}
            {data?.paused && <Status level="warning" label="nuovi ingressi in pausa" />}</p>
          <p className="muted">Perdite consecutive: {data?.consecutive_losses ?? 0} (pausa dopo {p.max_consecutive_losses}) · pausa fino a: {fmtTime(data?.paused_until)}</p>
          {STATIC && <div className="note">{READ_ONLY_MSG}</div>}
          <div className="filters">
            <button disabled={STATIC} onClick={() => act("pause", "Sospendere i nuovi ingressi?")}>⏸ Pausa</button>
            <button disabled={STATIC} onClick={() => act("resume", "Riprendere il trading? Il kill switch verrà disattivato e il riferimento del drawdown azzerato.")}>▶️ Riprendi</button>
            <button className="danger" disabled={STATIC} onClick={() => act("kill", "Attivare il KILL SWITCH? Nessun nuovo ingresso finché non riprendi.")}>🛑 Kill switch</button>
          </div>
          <h3>Trading reale</h3>
          {data?.live_gates?.length ? (
            <>
              <Status level="good" label={`bloccato (${data.live_gates.length} condizioni non soddisfatte)`} />
              <ul className="list">{data.live_gates.map((g: string) => <li key={g}>{g}</li>)}</ul>
            </>
          ) : <Status level="critical" label="tutte le condizioni per il trading reale sono soddisfatte" />}
        </div>
        <div className="card">
          <h2>Esposizione per token (SOL)</h2>
          <HBars data={exposure} fmt={(v) => v.toFixed(3)} />
          <h3>Limiti del profilo</h3>
          <table><tbody>
            <tr><td>Max per posizione</td><td>{fmtPctPlain(p.max_position_pct, 0)} del capitale</td></tr>
            <tr><td>Impatto di prezzo massimo</td><td>{fmtPctPlain(p.max_price_impact_pct)}</td></tr>
            <tr><td>Quota massima del pool</td><td>{fmtPctPlain(p.max_pool_share_pct)}</td></tr>
            <tr><td>Cuscinetto per gap/rug nel sizing</td><td>{fmtPctPlain(p.gap_risk_buffer_pct, 0)}</td></tr>
            <tr><td>Score minimo</td><td>{p.min_score}</td></tr>
            <tr><td>Cooldown stesso token</td><td>{p.cooldown_same_token_min} min</td></tr>
          </tbody></table>
        </div>
      </div>
    </>
  );
}
