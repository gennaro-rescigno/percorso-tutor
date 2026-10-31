import { useEffect, useState } from "react";
import { getJSON, num, pct, signedPct } from "../api";
import { CalibrationChart, LineChart } from "../components/Charts";
import { MARKET_NAMES, Tile } from "../components/Common";
import type { Agg, Backtest } from "../types";

interface OppRow {
  id: number;
  match: string;
  league: string | null;
  label: string;
  status: string;
  first_seen: string;
  minute: number | null;
  score: string;
  odds: number;
  closing_odds: number | null;
  p_model: number;
  ev_cons: number;
  confidence: string;
  result: string | null;
  profit: number | null;
  reason: string | null;
}

function AggTable({ title, rows, nameMap }: { title: string; rows: Record<string, Agg>; nameMap?: Record<string, string> }) {
  const keys = Object.keys(rows);
  return (
    <div className="card">
      <h2>{title}</h2>
      {keys.length === 0 ? (
        <div className="small muted">Nessun dato ancora.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th></th><th className="num">N</th><th className="num">Vinte</th><th className="num">% vinte</th><th className="num">P media</th><th className="num">Quota media</th><th className="num">Profitto</th><th className="num">Yield</th><th className="num">EV atteso</th><th className="num">CLV</th></tr>
            </thead>
            <tbody>
              {keys.map((k) => {
                const a = rows[k];
                return (
                  <tr key={k}>
                    <td>{nameMap?.[k] ?? k}</td>
                    <td className="num">{a.n}</td>
                    <td className="num">{a.wins ?? "—"}</td>
                    <td className="num">{pct(a.hit_rate)}</td>
                    <td className="num">{pct(a.avg_p_model)}</td>
                    <td className="num">{num(a.avg_odds)}</td>
                    <td className={`num ${(a.profit ?? 0) >= 0 ? "pos" : "neg"}`}>{num(a.profit)}u</td>
                    <td className="num">{signedPct(a.yield)}</td>
                    <td className="num">{signedPct(a.avg_ev_cons_expected)}</td>
                    <td className="num">{signedPct(a.clv)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function HistoryPage({ tick }: { tick: string | null }) {
  const [bt, setBt] = useState<Backtest | null>(null);
  const [rows, setRows] = useState<OppRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([getJSON<Backtest>("/api/backtest"), getJSON<OppRow[]>("/api/opportunities?limit=200")])
      .then(([b, r]) => { setBt(b); setRows(r); setErr(null); })
      .catch((e) => setErr(String(e)));
  }, [tick]);
  if (err) return <div className="banner critical">{err}</div>;
  if (!bt) return <div className="muted">Caricamento…</div>;
  const o = bt.overall;
  return (
    <>
      <div className="banner"><div><strong>Come leggere questi numeri</strong>{bt.note}</div></div>
      <div className="kpis">
        <Tile label="Selezioni chiuse" value={o.n} sub={`${bt.pending} in attesa di esito`} />
        <Tile label="% vinte" value={pct(o.hit_rate)} sub={`probabilità media stimata ${pct(o.avg_p_model)}`} />
        <Tile label="Profitto (stake 1u)" value={`${num(o.profit)}u`} sub={`max drawdown ${num(bt.max_drawdown)}u`} />
        <Tile label="Yield" value={signedPct(o.yield)} sub={`ROI su bankroll ${signedPct(o.roi_bankroll)}`} />
        <Tile label="EV prudenziale atteso" value={signedPct(o.avg_ev_cons_expected)} sub={`CLV medio ${signedPct(o.clv)}`} />
      </div>
      <div className="grid2">
        <div className="card">
          <h2>Profitto cumulato</h2>
          {bt.equity.length < 2 ? (
            <div className="empty small">Servono almeno 2 selezioni chiuse per disegnare la curva.</div>
          ) : (
            <LineChart
              series={[{ name: "Profitto cumulato (u)", color: "var(--accent)", points: bt.equity.map((e, i) => ({ x: i + 1, y: e.profit })) }]}
              xFormat={(v) => `#${Math.round(v)}`}
              yFormat={(v) => `${v.toFixed(1)}u`}
              xLabel="selezione n."
            />
          )}
        </div>
        <div className="card">
          <h2>Calibrazione delle probabilità (dati live)</h2>
          <CalibrationChart
            series={[
              { name: `Tutte le previsioni registrate (n=${bt.calibration_predictions.n})`, color: "var(--home)", bins: bt.calibration_predictions.bins },
              { name: `Opportunità segnalate (n=${bt.calibration_opportunities.n})`, color: "var(--away)", bins: bt.calibration_opportunities.bins },
            ]}
          />
          <div className="small muted">
            Brier {num(bt.calibration_predictions.brier, 4)} · log-loss {num(bt.calibration_predictions.logloss, 4)} (previsioni registrate)
          </div>
        </div>
      </div>
      <div style={{ display: "grid", gap: 16, marginTop: 16 }}>
        <AggTable title="Risultati per mercato" rows={bt.by_market} nameMap={MARKET_NAMES} />
        <AggTable title="Risultati per fascia di quota" rows={bt.by_odds_band} />
        <AggTable title="Risultati per livello di confidenza" rows={bt.by_confidence} />
        <AggTable title="Risultati per campionato" rows={bt.by_league} />
        <div className="card">
          <h2>Storico opportunità</h2>
          {rows.length === 0 ? (
            <div className="small muted">Nessuna opportunità registrata.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Rilevata</th><th>Partita</th><th>Selezione</th><th className="num">Min.</th><th className="num">Quota</th><th className="num">Ultima</th><th className="num">P stimata</th><th className="num">EV prud.</th><th>Stato</th><th>Esito</th><th className="num">Profitto</th></tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td className="small">{new Date(r.first_seen).toLocaleString("it-IT")}</td>
                      <td>{r.match}<div className="small muted">{r.league} · {r.score}</div></td>
                      <td>{r.label}<div className="small muted">{r.confidence}</div></td>
                      <td className="num">{r.minute ?? "—"}</td>
                      <td className="num">{num(r.odds)}</td>
                      <td className="num">{num(r.closing_odds)}</td>
                      <td className="num">{pct(r.p_model)}</td>
                      <td className="num">{signedPct(r.ev_cons)}</td>
                      <td className="small">{r.status}{r.reason ? <div className="muted">{r.reason}</div> : null}</td>
                      <td>{r.result ?? "—"}</td>
                      <td className="num">{r.profit === null ? "—" : `${num(r.profit)}u`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
