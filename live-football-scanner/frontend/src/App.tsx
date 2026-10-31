import { useEffect, useState } from "react";
import { ago, useLiveState } from "./api";
import FixtureDrawer from "./pages/FixtureDrawer";
import HistoryPage from "./pages/HistoryPage";
import LivePage from "./pages/LivePage";
import ModelPage from "./pages/ModelPage";
import SourcesPage from "./pages/SourcesPage";

type Tab = "live" | "history" | "model" | "sources";
const TABS: [Tab, string][] = [
  ["live", "Dashboard live"],
  ["history", "Storico & performance"],
  ["model", "Modello & validazione"],
  ["sources", "Fonti dati"],
];

function loadTab(): Tab {
  try {
    const t = localStorage.getItem("lfs-tab") as Tab | null;
    if (t && TABS.some(([k]) => k === t)) return t;
  } catch {
    /* ignore */
  }
  return "live";
}

export default function App() {
  const { state, setState, connected, error } = useLiveState();
  const [tab, setTab] = useState<Tab>(loadTab);
  const [open, setOpen] = useState<number | null>(null);
  const [now, setNow] = useState(Date.now());
  const [theme, setTheme] = useState<string>(() => {
    try {
      return localStorage.getItem("lfs-theme") ?? "auto";
    } catch {
      return "auto";
    }
  });
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  useEffect(() => {
    if (theme === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("lfs-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);
  const choose = (t: Tab) => {
    setTab(t);
    try {
      localStorage.setItem("lfs-tab", t);
    } catch {
      /* ignore */
    }
  };
  const af = state?.providers.api_football;
  const afStatus = !af ? "muted" : !af.configured ? "critical" : af.last_error ? "warning" : af.last_ok ? "good" : "muted";
  const stale = state?.updated_at ? now - new Date(state.updated_at).getTime() > 3 * 60 * 1000 : false;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          Live Football Intelligence Scanner
          <small>analisi statistica in-play · quote ≥ 1.75 · solo dati reali</small>
        </div>
        <nav className="tabs">
          {TABS.map(([k, label]) => (
            <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => choose(k)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="spacer" />
        <div className="pills">
          <span className="pill"><span className={`dot ${connected ? "good" : "warning"}`} />{connected ? "Aggiornamento in tempo reale" : "Riconnessione…"}</span>
          <span className="pill"><span className={`dot ${afStatus}`} />API-Football {af?.configured ? (af.last_error ? "errore" : "ok") : "non configurata"}</span>
          <span className="pill">Agg. {ago(state?.updated_at, now)}</span>
          <select aria-label="Tema" value={theme} onChange={(e) => setTheme(e.target.value)}>
            <option value="auto">Tema: sistema</option>
            <option value="light">Chiaro</option>
            <option value="dark">Scuro</option>
          </select>
        </div>
      </header>

      {error && !state && <div className="banner critical"><div><strong>Backend non raggiungibile</strong>{error}. Avvia il server FastAPI (vedi README).</div></div>}
      {state?.message && <div className="banner warning"><div><strong>Stato</strong>{state.message}</div></div>}
      {af?.last_error && <div className="banner critical"><div><strong>Errore API-Football</strong>{af.last_error}</div></div>}
      {state?.providers.scanner.last_error && <div className="banner warning"><div><strong>Scanner</strong>{state.providers.scanner.last_error}</div></div>}
      {stale && <div className="banner warning"><div><strong>Dati non aggiornati</strong>L'ultimo ciclo risale a più di 3 minuti fa: le opportunità mostrate potrebbero non essere più valide.</div></div>}

      {state && tab === "live" && <LivePage state={state} now={now} onOpen={setOpen} />}
      {state && tab === "history" && <HistoryPage tick={state.updated_at} />}
      {tab === "model" && <ModelPage />}
      {state && tab === "sources" && <SourcesPage state={state} now={now} setState={setState} />}
      {open !== null && <FixtureDrawer id={open} onClose={() => setOpen(null)} tick={state?.updated_at ?? null} />}
    </div>
  );
}
