import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { getToken, setToken, usePoll } from "./api";
import { ModeBadge, Status } from "./components/ui";
import "./theme.css";
import BacktestLab from "./pages/BacktestLab";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Overview from "./pages/Overview";
import Performance from "./pages/Performance";
import Positions from "./pages/Positions";
import Risk from "./pages/Risk";
import Scanner from "./pages/Scanner";
import TokenPage from "./pages/Token";

const NAV = [
  ["/", "Overview"], ["/scanner", "Market Scanner"], ["/positions", "Posizioni"], ["/performance", "Performance"],
  ["/backtest", "Backtest Lab"], ["/risk", "Risk Management"], ["/logs", "Log e attività"],
];

function Shell({ onLogout }: { onLogout: () => void }) {
  const { data } = usePoll<any>("/overview", 30000);
  const w = data?.worker ?? {};
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">Memecoin Intelligence<small>Solana · scoring · paper trading</small></div>
        <nav className="nav">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>{label}</NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <button onClick={onLogout}>Esci</button>
      </aside>
      <main className="main">
        <div className="topbar">
          <ModeBadge mode={w.mode} />
          {w.worker_alive ? <Status level="good" label="worker attivo" /> : <Status level="critical" label="worker non raggiungibile" />}
          {data?.summary?.kill_switch && <Status level="critical" label="KILL SWITCH" />}
          {data?.summary?.paused && <Status level="warning" label="in pausa" />}
          {w.sol_eur && <span className="badge">1 SOL = {w.sol_eur.toFixed(2).replace(".", ",")} €</span>}
        </div>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/token/:address" element={<TokenPage />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/backtest" element={<BacktestLab />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  const [authed, setAuthed] = useState(!!getToken());
  useEffect(() => {
    const h = () => setAuthed(false);
    window.addEventListener("mci-logout", h);
    return () => window.removeEventListener("mci-logout", h);
  }, []);
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;
  return <Shell onLogout={() => { setToken(null); setAuthed(false); }} />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
