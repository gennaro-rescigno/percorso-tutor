import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePoll } from "../api";
import { Column, DataTable, ErrorBox } from "../components/ui";
import { fmtNum, fmtPct, fmtPrice, fmtSol, fmtTime, signClass } from "../format";

export default function Positions() {
  const [status, setStatus] = useState("open");
  const { data, error } = usePoll<any>(`/positions?status=${status}`, 15000);
  const nav = useNavigate();
  const cols: Column<any>[] = [
    { key: "symbol", label: "Token", render: (r) => <b>{r.symbol}</b> },
    { key: "strategy", label: "Strategia" },
    { key: "status", label: "Stato" },
    { key: "opened_at", label: "Apertura", render: (r) => fmtTime(r.opened_at) },
    { key: "entry_price", label: "Ingresso", num: true, render: (r) => fmtPrice(r.entry_price) },
    { key: "current_price", label: "Corrente", num: true, render: (r) => (r.status === "open" ? fmtPrice(r.current_price) : "—") },
    { key: "stake_sol", label: "Stake", num: true, render: (r) => fmtSol(r.stake_sol) },
    { key: "qty", label: "Quantità", num: true, render: (r) => fmtNum(r.status === "open" ? r.qty : r.qty_initial) },
    { key: "stop_price", label: "Stop", num: true, render: (r) => fmtPrice(r.stop_price) },
    { key: "tp", label: "Take profit", sortable: false,
      render: (r) => (r.take_profits ?? []).map((t: any) => `${fmtPrice(t.price)} (${Math.round(t.fraction * 100)}%)`).join(" · ") || "trailing" },
    { key: "pnl_sol", label: "P/L", num: true, render: (r) => <span className={signClass(r.pnl_sol)}>{fmtSol(r.pnl_sol)}</span> },
    { key: "return_pct", label: "Rendimento", num: true, render: (r) => <span className={signClass(r.return_pct)}>{fmtPct(r.return_pct)}</span> },
    { key: "fees_sol", label: "Commissioni", num: true, render: (r) => fmtSol(r.fees_sol) },
    { key: "slippage_sol", label: "Slippage", num: true, render: (r) => fmtSol(r.slippage_sol) },
    { key: "duration_min", label: "Durata", num: true, render: (r) => (r.duration_min == null ? "n/d" : `${Math.round(r.duration_min)} min`) },
    { key: "exit_reason", label: "Motivo uscita", render: (r) => <span className="muted">{r.exit_reason ?? ""}</span> },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Posizioni</h1>
      <ErrorBox error={error} />
      <div className="tabs">
        {[["open", "Aperte"], ["closed", "Chiuse"], ["all", "Tutte"]].map(([k, l]) => (
          <button key={k} className={status === k ? "active" : ""} onClick={() => setStatus(k)}>{l}</button>
        ))}
      </div>
      <div className="card">
        <DataTable rows={data?.positions ?? []} columns={cols} onRowClick={(r) => nav(`/token/${r.token}`)}
                   initialSort={{ key: "opened_at", desc: true }} empty="Nessuna posizione" />
      </div>
      <div className="note">Il P/L delle posizioni aperte è valutato al prezzo di mercato; la vendita reale subirebbe impatto e commissioni.</div>
    </>
  );
}
