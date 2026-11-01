import { useEffect, useMemo, useState } from "react";
import { STATIC, api, usePoll } from "../api";
import { MultiLine } from "../components/charts";
import { ErrorBox } from "../components/ui";
import { fmtNum, fmtPct, fmtPctPlain, fmtSol, fmtTime } from "../format";

const METRICS: [string, string, (v: any) => string][] = [
  ["final_capital_sol", "Capitale finale", (v) => fmtSol(v)],
  ["net_profit_sol", "Profitto netto", (v) => fmtSol(v)],
  ["return_pct", "Rendimento", (v) => fmtPct(v)],
  ["n_trades", "Operazioni", (v) => fmtNum(v)],
  ["win_rate", "Win rate", (v) => fmtPctPlain(v)],
  ["profit_factor", "Profit factor", (v) => (v == null ? "n/d" : fmtNum(v, 2))],
  ["expectancy_pct", "Expectancy / trade", (v) => fmtPct(v)],
  ["max_drawdown_pct", "Max drawdown", (v) => fmtPctPlain(v)],
  ["mc_max_dd_p95", "Max DD Monte Carlo p95", (v) => fmtPctPlain(v)],
  ["sharpe", "Sharpe", (v) => (v == null ? "n/d" : fmtNum(v, 2))],
  ["max_consecutive_losses", "Serie max perdite", (v) => fmtNum(v)],
  ["avg_hold_minutes", "Durata media (min)", (v) => fmtNum(v)],
  ["total_fees_sol", "Commissioni", (v) => fmtSol(v)],
  ["total_slippage_sol", "Slippage", (v) => fmtSol(v)],
  ["max_capital_used_sol", "Capitale max investito", (v) => fmtSol(v)],
  ["robust", "Robusto", (v) => (v ? "SÌ" : "NO")],
];

export default function BacktestLab() {
  const opts = usePoll<any>("/config/options", 0);
  const runs = usePoll<any>("/backtests", 5000);
  const [strategies, setStrategies] = useState<string[]>(["B"]);
  const [profile, setProfile] = useState("moderate");
  const [exitPolicy, setExitPolicy] = useState("ladder_trailing");
  const [capital, setCapital] = useState(2);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [dataset, setDataset] = useState("recorded");
  const [params, setParams] = useState("{}");
  const [exitOv, setExitOv] = useState("{}");
  const [profileOv, setProfileOv] = useState("{}");
  const [err, setErr] = useState<string | null>(null);
  const [cmp, setCmp] = useState<number[]>([]);
  const [details, setDetails] = useState<Record<number, any>>({});

  useEffect(() => {
    const st = opts.data?.strategies ?? [];
    const sel = Object.fromEntries(st.filter((s: any) => strategies.includes(s.code)).map((s: any) => [s.code, s.params]));
    setParams(JSON.stringify(sel, null, 2));
  }, [opts.data, strategies.join(",")]);

  useEffect(() => {
    cmp.forEach(async (id) => {
      if (!details[id] || details[id].status !== "done") {
        const d = await api(`/backtests/${id}`);
        setDetails((x) => ({ ...x, [id]: d }));
      }
    });
  }, [cmp, runs.data]);

  async function run() {
    setErr(null);
    try {
      const body = {
        name: `${strategies.join("+")} ${profile} ${exitPolicy}`, strategies, profile, exit_policy: exitPolicy, capital_sol: capital,
        start: start || null, end: end || null, dataset, strategy_params: JSON.parse(params || "{}"),
        exit_overrides: JSON.parse(exitOv || "{}"), profile_overrides: JSON.parse(profileOv || "{}"),
      };
      const r = await api<any>("/backtests", { method: "POST", body: JSON.stringify(body) });
      setCmp((c) => [r.id, ...c].slice(0, 2));
      runs.reload();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  const compared = cmp.map((id) => details[id]).filter(Boolean);
  const curve = useMemo(() => {
    // index both equity curves by sample number (different periods can't share a time axis)
    const rows: any[] = [];
    compared.forEach((d: any, i: number) => {
      (d.equity_curve ?? []).forEach((p: any, j: number) => {
        rows[j] = rows[j] ?? { step: j };
        rows[j][`r${i}`] = p[1];
      });
    });
    return rows;
  }, [JSON.stringify(compared.map((d: any) => [d.id, d.status]))]);

  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Backtest Lab</h1>
      <ErrorBox error={err || opts.error} />
      <div className="card">
        <h2>Nuovo backtest</h2>
        <div className="form-grid">
          <label className="wide">Strategie
            <div className="filters" style={{ marginBottom: 0 }}>
              {(opts.data?.strategies ?? []).map((s: any) => (
                <label key={s.code} className="muted" style={{ display: "inline-flex", gap: 4 }}>
                  <input type="checkbox" checked={strategies.includes(s.code)}
                         onChange={(e) => setStrategies(e.target.checked ? [...strategies, s.code] : strategies.filter((x) => x !== s.code))} />
                  {s.code} {s.name}
                </label>
              ))}
            </div>
          </label>
          <label>Profilo di rischio
            <select value={profile} onChange={(e) => setProfile(e.target.value)}>
              {Object.keys(opts.data?.profiles ?? {}).map((k) => <option key={k}>{k}</option>)}
            </select></label>
          <label>Gestione uscita (stop / TP)
            <select value={exitPolicy} onChange={(e) => setExitPolicy(e.target.value)}>
              {Object.keys(opts.data?.exit_policies ?? {}).map((k) => <option key={k}>{k}</option>)}
            </select></label>
          <label>Capitale iniziale (SOL)<input type="number" step="0.1" min="0.1" value={capital} onChange={(e) => setCapital(+e.target.value)} /></label>
          <label>Dal<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label>Al<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <label>Dati
            <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
              <option value="recorded">registrati dallo scanner (reali)</option>
              <option value="imported">storico importato da Dune (reali)</option>
              <option value="synthetic">sintetici (solo test del motore)</option>
            </select></label>
        </div>
        <div className="grid cols-2 section">
          <label className="muted">Parametri strategie (JSON)<textarea value={params} onChange={(e) => setParams(e.target.value)} /></label>
          <div className="grid">
            <label className="muted">Override uscita, es. {"{\"fixed_stop_pct\":0.15,\"take_profits\":[[0.4,0.5]]}"}
              <textarea style={{ minHeight: 70 }} value={exitOv} onChange={(e) => setExitOv(e.target.value)} /></label>
            <label className="muted">Override rischio/stake, es. {"{\"risk_per_trade_pct\":0.01,\"max_position_pct\":0.1}"}
              <textarea style={{ minHeight: 70 }} value={profileOv} onChange={(e) => setProfileOv(e.target.value)} /></label>
          </div>
        </div>
        <button className="primary" onClick={run} disabled={STATIC || !strategies.length}>Lancia backtest</button>
        {STATIC && <div className="note">Nella dashboard pubblica i backtest non si lanciano: si eseguono dal workflow GitHub "memecoin-backtest".</div>}
        <div className="note">Seleziona fino a due run nella tabella sotto per confrontarli.</div>
      </div>

      <div className="card section">
        <h2>Run</h2>
        <div className="table-wrap"><table>
          <thead><tr><th>Confronta</th><th>#</th><th>Nome</th><th>Stato</th><th>Data</th><th className="num">Rendimento</th><th className="num">Trade</th><th className="num">Max DD</th><th>Dati</th></tr></thead>
          <tbody>
            {(runs.data?.runs ?? []).map((r: any) => (
              <tr key={r.id}>
                <td><input type="checkbox" checked={cmp.includes(r.id)} onChange={(e) => setCmp(e.target.checked ? [r.id, ...cmp].slice(0, 2) : cmp.filter((x) => x !== r.id))} /></td>
                <td>{r.id}</td><td>{r.name}</td><td>{r.status}{r.error ? ` – ${r.error}` : ""}</td><td>{fmtTime(r.created_at)}</td>
                <td className="num">{fmtPct(r.metrics?.return_pct)}</td><td className="num">{fmtNum(r.metrics?.n_trades)}</td>
                <td className="num">{fmtPctPlain(r.metrics?.max_drawdown_pct)}</td>
                <td>{r.data_info?.source}{r.data_info && !r.data_info.survivorship_free ? " ⚠️ survivorship" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>

      {compared.length > 0 && (
        <div className="grid cols-2 section">
          <div className="card">
            <h2>Confronto metriche</h2>
            <table>
              <thead><tr><th>Metrica</th>{compared.map((d: any) => <th key={d.id}>#{d.id} {d.name}</th>)}</tr></thead>
              <tbody>{METRICS.map(([k, l, f]) => (
                <tr key={k}><td>{l}</td>{compared.map((d: any) => <td key={d.id}>{d.metrics ? f(d.metrics[k]) : d.status}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
          <div className="card">
            <h2>Equity (SOL) per campione</h2>
            <MultiLine data={curve} x="step" series={compared.map((d: any, i: number) => ({ key: `r${i}`, name: `#${d.id}` }))} fmt={(v) => v.toFixed(3)} />
            {compared.map((d: any) => d.report_md && (
              <details key={d.id}><summary>Report #{d.id}</summary><pre className="report">{d.report_md}</pre></details>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
