import { useNavigate } from "react-router-dom";
import { usePoll } from "../api";
import { Column, DataTable, ErrorBox, Kpi, Status } from "../components/ui";
import { fmtNum, fmtPctPlain, fmtTime } from "../format";

const outcome = (l: any) => {
  if (!l) return <span className="muted">in attesa (4 h)</span>;
  if (l.no_price) return <span className="muted">nessun prezzo</span>;
  const tag = l.first_passage === "2x_first" ? "×2" : l.first_passage === "half_first" ? "÷2" : "stabile";
  return <span title="×2 = raddoppiato prima di dimezzarsi; ÷2 = dimezzato prima; stabile = nessuno dei due in 4 h">{tag}{l.rug_60m ? " · crollo" : ""}{l.incomplete ? " (incompleto)" : ""}</span>;
};

export default function Launches() {
  const { data, error } = usePoll<any>("/launches", 30000);
  const nav = useNavigate();
  const st = data?.stream ?? {};
  const tr = data?.tracker ?? {};
  const cols: Column<any>[] = [
    { key: "created_at", label: "Creato", render: (r) => fmtTime(r.created_at) },
    { key: "symbol", label: "Token", render: (r) => <b>{r.symbol ?? r.mint.slice(0, 6)}</b> },
    { key: "mayhem", label: "Tipo", render: (r) => (r.mayhem ? <span className="muted">mayhem (non organico)</span> : "normale") },
    { key: "trades", label: "Operazioni", num: true, value: (r) => r.stats?.trades, render: (r) => fmtNum(r.stats?.trades) },
    { key: "wallets", label: "Wallet", num: true, value: (r) => r.stats?.wallets, render: (r) => fmtNum(r.stats?.wallets) },
    { key: "progress", label: "Curva", num: true, value: (r) => r.stats?.progress_pct, render: (r) => (r.complete_at ? "migrato" : r.stats?.progress_pct != null ? `${fmtNum(r.stats.progress_pct, 1)}%` : "n/d") },
    { key: "buyers5", label: "Acquirenti a 5 min", num: true, value: (r) => r.t5?.unique_buyers, render: (r) => fmtNum(r.t5?.unique_buyers) },
    { key: "pressure", label: "Pressione acquisto", num: true, value: (r) => r.t5?.buy_pressure, render: (r) => fmtPctPlain(r.t5?.buy_pressure) },
    { key: "snipers", label: "Sniper %", num: true, value: (r) => r.t5?.sniper_pct, render: (r) => (r.t5?.sniper_pct == null ? "n/d" : `${fmtNum(r.t5.sniper_pct, 1)}%`) },
    { key: "risk", label: "Rischio", num: true, value: (r) => r.t5?.risk, render: (r) => fmtNum(r.t5?.risk) },
    { key: "opp", label: "Opportunità", num: true, value: (r) => r.t5?.opportunity, render: (r) => fmtNum(r.t5?.opportunity) },
    { key: "outcome", label: "Esito reale", render: (r) => outcome(r.t5?.labels) },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Lanci pump.fun in tempo reale</h1>
      <ErrorBox error={error} />
      <div className="note">Dati gratuiti letti direttamente dalla blockchain Solana (WebSocket pubblico, eventi ufficiali di pump.fun).
        Rischio e opportunità sono indici euristici 0-100, <b>non probabilità</b>.</div>
      <div className="grid kpis section">
        <Kpi label="Stream blockchain" value={st.connected ? <Status level="good" label="connesso" /> : <Status level="critical" label="non connesso" />}
             sub={st.last_error ? `ultimo errore: ${st.last_error}` : st.reconnects ? `riconnessioni: ${st.reconnects}` : undefined} />
        <Kpi label="Lanci nell'ultima ora" value={fmtNum(tr.launches_1h)} sub={`24 h: ${fmtNum(tr.launches_24h)}`} />
        <Kpi label="Operazioni decodificate" value={fmtNum(st.trades)} sub={`transazioni fallite scartate: ${fmtNum(st.skipped_failed)}`} />
        <Kpi label="Interruzioni stream (24 h)" value={fmtNum(tr.gaps_24h)} />
      </div>
      <div className="card section">
        <DataTable rows={data?.launches ?? []} columns={cols} onRowClick={(r) => nav(`/token/${r.mint}`)}
                   initialSort={{ key: "created_at", desc: true }} empty="Nessun lancio registrato ancora" />
      </div>
    </>
  );
}
