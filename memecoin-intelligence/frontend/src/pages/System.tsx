import { usePoll } from "../api";
import { ErrorBox, Kpi, Status } from "../components/ui";
import { fmtNum, fmtSol, fmtTime } from "../format";

const mb = (b?: number | null) => (b == null ? "n/d" : `${fmtNum(b / 1e6, 1)} MB`);
const DATASET: Record<string, string> = {
  launches: "lanci registrati", launches_24h: "lanci nelle ultime 24 h", early_trades: "operazioni iniziali salvate",
  feature_snapshots: "istantanee del feature store", labeled: "istantanee con esito reale",
  wallet_profiles: "wallet analizzati", stream_candles: "candele dallo stream",
};

export default function System() {
  const { data, error } = usePoll<any>("/system", 30000);
  const w = data?.worker ?? {};
  const cs = data?.chain_stream ?? {};
  const rpc = data?.rpc ?? {};
  const nc = data?.network_costs ?? {};
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Salute del sistema</h1>
      <ErrorBox error={error} />
      <div className="grid kpis section">
        <Kpi label="Worker" value={w.worker_alive ? <Status level="good" label="attivo" /> : <Status level="critical" label="non raggiungibile" />}
             sub={`ciclo ${fmtNum(w.cycle)} · ultimo ${fmtTime(w.last_cycle)}`} />
        <Kpi label="Stream blockchain" value={cs.connected ? <Status level="good" label="connesso" /> : <Status level="critical" label="non connesso" />}
             sub={`${fmtNum(cs.trades)} operazioni · ${fmtNum(cs.reconnects)} riconnessioni`} />
        <Kpi label="Token seguiti" value={fmtNum(w.tracked)} />
        <Kpi label="Database" value={mb(data?.db_size_bytes)} />
        <Kpi label="Priority fee usata" value={fmtSol(data?.costs_in_use?.priority_fee_sol, 6)}
             sub={nc.priority_p75_sol != null ? `misurata (75° perc.): ${fmtSol(nc.priority_p75_sol, 6)}` : "misura non ancora disponibile"} />
        <Kpi label="Tip Jito (mediana)" value={fmtSol(nc.jito_50_sol, 6)} sub="solo informativo: il paper trading non lo paga" />
      </div>
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Fonti dati</h2>
          <table><tbody>
            {Object.entries(data?.sources ?? {}).map(([k, v]: any) => (
              <tr key={k}><td>{k}</td><td><Status level={v.ok ? "good" : "critical"} label={v.ok ? "OK" : "errore"} /></td>
                <td className="muted">{v.ok ? fmtTime(v.at) : v.error}</td></tr>
            ))}
            <tr><td>PumpPortal (nuovi token)</td><td><Status level={w.pumpportal_connected ? "good" : "warning"} label={w.pumpportal_connected ? "connesso" : "non connesso"} /></td><td /></tr>
            <tr><td>Chiave Jupiter gratuita</td><td>{w.jupiter_key ? "attiva" : "assente"}</td><td /></tr>
          </tbody></table>
        </div>
        <div className="card">
          <h2>RPC Solana (gratuito, con budget)</h2>
          <table><tbody>
            <tr><td>Chiamate</td><td className="num">{fmtNum(rpc.calls)}</td></tr>
            <tr><td>Risposte dalla cache</td><td className="num">{fmtNum(rpc.cache_hits)}</td></tr>
            <tr><td>Rinviate per budget</td><td className="num">{fmtNum(rpc.budget_refused)}</td></tr>
            <tr><td>Fallite</td><td className="num">{fmtNum(rpc.failed)}</td></tr>
            {(rpc.endpoints ?? []).map((e: any) => (
              <tr key={e.name}><td>{e.name}</td><td className="num">{e.available ? "disponibile" : "in pausa"} · ok {fmtNum(e.ok)} · 429 {fmtNum(e.rate_limited)} · errori {fmtNum(e.errors)}</td></tr>
            ))}
          </tbody></table>
          <div className="note">Analisi on-chain: {fmtNum(data?.onchain?.security_checks)} controlli di sicurezza, {fmtNum(data?.onchain?.wallet_analyses)} analisi wallet,
            {" "}{fmtNum(data?.onchain?.rugcheck_disagreements)} disaccordi con RugCheck (vale il dato on-chain).</div>
        </div>
        <div className="card">
          <h2>Raccolta dati</h2>
          <table><tbody>
            {Object.entries(data?.dataset ?? {}).map(([k, v]: any) => <tr key={k}><td>{DATASET[k] ?? k}</td><td className="num">{fmtNum(v)}</td></tr>)}
          </tbody></table>
        </div>
        <div className="card">
          <h2>Interruzioni dello stream (24 h)</h2>
          {(data?.stream_gaps_24h ?? []).length === 0 ? <div className="muted">nessuna</div> : (
            <table><tbody>{data.stream_gaps_24h.map(([a, b]: number[], i: number) => (
              <tr key={i}><td>{new Date(a * 1000).toLocaleString("it-IT")}</td><td className="num">{fmtNum((b - a) / 60, 1)} min</td></tr>
            ))}</tbody></table>
          )}
          <div className="note">Durante un'interruzione le caratteristiche dei lanci sono marcate "incomplete" e non entrano nella ricerca.</div>
        </div>
      </div>
      <div className="card section">
        <h2>Ultimi errori</h2>
        {(data?.recent_errors ?? []).length === 0 ? <div className="muted">nessun errore</div> : (
          <table><tbody>{data.recent_errors.map((e: any, i: number) => (
            <tr key={i}><td>{fmtTime(e.ts)}</td><td>{e.category}</td><td className="muted">{e.message}</td></tr>
          ))}</tbody></table>
        )}
      </div>
    </>
  );
}
