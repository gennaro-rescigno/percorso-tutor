import { useState } from "react";
import { usePoll } from "../api";
import { Column, DataTable, ErrorBox } from "../components/ui";
import { fmtTime } from "../format";

const CATS = [
  ["", "Tutto"], ["scan", "Token analizzati"], ["signal", "Segnali"], ["trade", "Acquisti/vendite"], ["order", "Ordini/transazioni"],
  ["error", "Errori"], ["param", "Modifiche parametri"], ["alert", "Alert"], ["risk", "Rischio"], ["system", "Sistema"],
];

export default function Logs() {
  const [cat, setCat] = useState("");
  const { data, error } = usePoll<any>(`/logs?limit=300${cat ? `&category=${cat}` : ""}`, 15000);
  const cols: Column<any>[] = [
    { key: "ts", label: "Ora", render: (r) => fmtTime(r.ts) },
    { key: "level", label: "Livello", render: (r) => (r.level === "error" ? "✕ errore" : r.level === "warn" ? "! avviso" : "info") },
    { key: "category", label: "Categoria" },
    { key: "message", label: "Messaggio", render: (r) => <span style={{ whiteSpace: "normal" }}>{r.message}</span> },
    { key: "token", label: "Token", render: (r) => <span className="mono muted">{r.token ? r.token.slice(0, 8) : ""}</span> },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Log e attività</h1>
      <ErrorBox error={error} />
      <div className="tabs">
        {CATS.map(([k, l]) => <button key={k} className={cat === k ? "active" : ""} onClick={() => setCat(k)}>{l}</button>)}
      </div>
      <div className="card"><DataTable rows={data?.events ?? []} columns={cols} empty="Nessun evento" /></div>
    </>
  );
}
