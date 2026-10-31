import { useEffect, useState } from "react";
import { ago, getJSON, postJSON } from "../api";
import type { LiveState, ProviderInfo } from "../types";

interface LogRow {
  ts: string;
  provider: string;
  endpoint: string;
  http_status: number | null;
  results: number | null;
  latency_ms: number | null;
  quota: Record<string, string | null> | null;
  error: string | null;
}

function ProviderCard({ name, p, now, desc }: { name: string; p: ProviderInfo; now: number; desc: string }) {
  const status = !p.configured ? ["muted", "Non configurato"] : p.last_error ? ["critical", "Errore"] : p.last_ok ? ["good", "Dati ricevuti"] : ["warning", "In attesa"];
  return (
    <div className="card">
      <h2>{name}</h2>
      <div className="small muted">{desc}</div>
      <div style={{ margin: "8px 0" }}>
        <span className="badge"><span className={`dot ${status[0]}`} />{status[1]}</span>
      </div>
      <div className="small">Ultima risposta valida: {p.last_ok ? `${new Date(p.last_ok).toLocaleString("it-IT")} (${ago(p.last_ok, now)})` : "mai"}</div>
      {p.last_error && <div className="small neg">Ultimo errore: {p.last_error}</div>}
      {p.quota && Object.keys(p.quota).length > 0 && (
        <table style={{ marginTop: 8 }}>
          <tbody>
            {Object.entries(p.quota).map(([k, v]) => <tr key={k}><td className="small">{k}</td><td className="num small">{v ?? "—"}</td></tr>)}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function SourcesPage({ state, now, setState }: { state: LiveState; now: number; setState: (s: LiveState) => void }) {
  const [rows, setRows] = useState<LogRow[]>([]);
  const [busy, setBusy] = useState(false);
  const load = () => getJSON<LogRow[]>("/api/provider-log?limit=100").then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, [state.updated_at]);
  const p = state.providers;
  return (
    <>
      <div className="banner">
        <div>
          <strong>Prova di provenienza dei dati</strong>
          Ogni chiamata ai provider viene registrata nel database (tabella <code>provider_log</code>) con stato HTTP, numero di risultati, latenza
          e header di quota restituiti dal server. Se una fonte non è configurata o non risponde, la dashboard resta vuota: nessun dato viene simulato.
        </div>
      </div>
      <div className="kpis" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <ProviderCard name="API-Football (api-sports.io)" p={p.api_football} now={now} desc="Partite live, eventi, statistiche, quote in-play (/odds/live), forma squadre." />
        <ProviderCard name="The Odds API" p={p.the_odds_api} now={now} desc="Opzionale: quote multi-bookmaker 1X2 / Over-Under (senza stato partita)." />
        <div className="card">
          <h2>Scanner</h2>
          <div className="small">Cicli completati: {p.scanner.cycles}</div>
          <div className="small">Ultimo ciclo: {ago(p.scanner.last_cycle_at, now)} ({p.scanner.last_cycle_ms ?? "—"} ms)</div>
          <div className="small">Intervallo: {p.scanner.poll_interval_s}s {p.scanner.paused ? "· IN PAUSA (quota)" : ""}</div>
          <div className="small">Modello: {p.model.loaded ? p.model.version : "non caricato"}</div>
          {p.scanner.last_error && <div className="small neg">{p.scanner.last_error}</div>}
          <button className="btn" style={{ marginTop: 8 }} disabled={busy} onClick={() => { setBusy(true); postJSON<LiveState>("/api/scan").then(setState).finally(() => { setBusy(false); load(); }); }}>
            {busy ? "Scansione…" : "Esegui scansione ora"}
          </button>
        </div>
      </div>
      <div className="card">
        <h2>Registro chiamate API (ultime 100)</h2>
        {rows.length === 0 ? (
          <div className="small muted">Nessuna chiamata registrata. Configura le chiavi API nel file .env.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Ora</th><th>Provider</th><th>Endpoint</th><th className="num">HTTP</th><th className="num">Risultati</th><th className="num">ms</th><th>Quota</th><th>Errore</th></tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td className="small">{new Date(r.ts).toLocaleTimeString("it-IT")}</td>
                    <td className="small">{r.provider}</td>
                    <td><code>{r.endpoint}</code></td>
                    <td className="num">{r.http_status ?? "—"}</td>
                    <td className="num">{r.results ?? "—"}</td>
                    <td className="num">{r.latency_ms ?? "—"}</td>
                    <td className="small">{r.quota ? Object.entries(r.quota).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`).join(" · ") : ""}</td>
                    <td className="small neg">{r.error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2>Mercati del feed non mappati</h2>
        <div className="small muted">Nomi di mercato ricevuti ma esclusi perché la loro regola di liquidazione non è supportata o non è univoca (es. handicap asiatico in-play, "resto della partita").</div>
        {p.unmapped_markets.length === 0 ? <div className="small muted">Nessuno.</div> : (
          <div className="chips" style={{ marginTop: 8 }}>{p.unmapped_markets.map(([n, c]) => <span key={n} className="chip">{n} ({c})</span>)}</div>
        )}
      </div>
    </>
  );
}
