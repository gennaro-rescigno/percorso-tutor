import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePoll } from "../api";
import { Column, DataTable, ErrorBox, RiskBadge } from "../components/ui";
import { fmtAge, fmtNum, fmtPct, fmtPrice, fmtUsd, signClass } from "../format";

const SORTS = [
  ["score", "Score"], ["volume", "Volume"], ["momentum", "Momentum"], ["mcap", "Market cap"],
  ["growth", "Crescita"], ["liquidity", "Liquidità"], ["risk", "Rischio"], ["recent", "Più recenti"],
];

export default function Scanner() {
  const [sort, setSort] = useState("score");
  const [q, setQ] = useState("");
  const [excluded, setExcluded] = useState(false);
  const path = `/scanner?sort=${sort}&limit=300&include_excluded=${excluded}${q ? `&q=${encodeURIComponent(q)}` : ""}`;
  const { data, error } = usePoll<any>(path, 30000);
  const nav = useNavigate();
  const cols: Column<any>[] = [
    { key: "symbol", label: "Token", render: (r) => <b>{r.symbol ?? r.address.slice(0, 6)}</b> },
    { key: "score", label: "Score", num: true, render: (r) => (r.score == null ? "n/d" : `${Math.round(r.score)}`) },
    { key: "label", label: "Valutazione", render: (r) => r.label ?? "n/d" },
    { key: "price_usd", label: "Prezzo", num: true, render: (r) => fmtPrice(r.price_usd) },
    { key: "mcap_usd", label: "Market cap", num: true, render: (r) => fmtUsd(r.mcap_usd) },
    { key: "volume_h24", label: "Volume 24h", num: true, render: (r) => fmtUsd(r.volume_h24) },
    { key: "liquidity_usd", label: "Liquidità", num: true, render: (r) => fmtUsd(r.liquidity_usd) },
    { key: "change_h1", label: "1h", num: true, render: (r) => <span className={signClass(r.change_h1)}>{fmtPct(r.change_h1 == null ? null : r.change_h1 / 100)}</span> },
    { key: "age_hours", label: "Età", num: true, render: (r) => fmtAge(r.age_hours) },
    { key: "holders", label: "Holder", num: true, render: (r) => fmtNum(r.holders) },
    { key: "social", label: "Social (Reddit 24h)", sortable: false,
      render: (r) => (r.social_growth ? `${r.social_growth.unique_authors} autori` : <span className="muted">n/d</span>) },
    { key: "risk", label: "Rischio", render: (r) => <RiskBadge risk={r.risk} /> },
    { key: "dex", label: "DEX", render: (r) => r.dex ?? "n/d" },
    { key: "status", label: "Stato", render: (r) => r.status },
    { key: "coverage", label: "Copertura dati", num: true, render: (r) => (r.coverage == null ? "n/d" : `${Math.round(r.coverage * 100)}%`) },
    { key: "exclusion", label: "Motivo esclusione", sortable: false,
      render: (r) => <span className="muted" style={{ whiteSpace: "normal", display: "inline-block", minWidth: 220 }}>{r.exclusion ?? ""}</span> },
  ];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Live Market Scanner</h1>
      <ErrorBox error={error} />
      <div className="filters">
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Ordina per">
          {SORTS.map(([k, l]) => <option key={k} value={k}>Ordina: {l}</option>)}
        </select>
        <input placeholder="Cerca simbolo o indirizzo" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="muted"><input type="checkbox" checked={excluded} onChange={(e) => setExcluded(e.target.checked)} /> mostra esclusi</label>
        <span className="muted">{data?.tokens?.length ?? 0} token · aggiornamento ogni 30 s</span>
      </div>
      <div className="card">
        <DataTable rows={data?.tokens ?? []} columns={cols} onRowClick={(r) => nav(`/token/${r.address}`)}
                   empty="Nessun token ancora registrato dallo scanner" />
      </div>
      <div className="note">I token esclusi dai filtri di sicurezza non vengono mai acquistati, qualunque sia lo score. "n/d" = dato non fornito dalle fonti (mai considerato positivo).</div>
    </>
  );
}
