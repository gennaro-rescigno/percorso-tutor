import { useEffect, useState } from "react";
import { getJSON, minuteLabel, num, pct, signedPct } from "../api";
import { LineChart } from "../components/Charts";
import { ConfidenceBadge, MODEL_NAMES, STAT_LABELS } from "../components/Common";
import type { FixtureDetail, SideStats, TeamForm } from "../types";

const COMPARE = ["shots", "sot", "shots_off", "blocked", "shots_in_box", "corners", "possession", "xg", "saves", "fouls", "yellow", "red"];

function StatRow({ name, h, a }: { name: string; h: number | null | undefined; a: number | null | undefined }) {
  const hv = h ?? 0;
  const av = a ?? 0;
  const max = Math.max(hv, av, 1e-9);
  const fmt = (v: number | null | undefined) => (v === null || v === undefined ? "n.d." : Number.isInteger(v) ? String(v) : v.toFixed(2));
  return (
    <div className="statrow">
      <div className="l">{fmt(h)}</div>
      <div className="bar-l"><span style={{ width: `${(hv / max) * 100}%` }} /></div>
      <div className="name">{name}</div>
      <div className="bar-r"><span style={{ width: `${(av / max) * 100}%` }} /></div>
      <div className="r">{fmt(a)}</div>
    </div>
  );
}

function WindowTable({ d }: { d: FixtureDetail }) {
  const w = d.windows;
  if (!w) return null;
  const rows: { k: keyof NonNullable<FixtureDetail["windows"]>; label: string }[] = [
    { k: "w5", label: "Ultimi 5'" },
    { k: "w10", label: "Ultimi 10'" },
    { k: "w15", label: "Ultimi 15'" },
  ];
  const cell = (s: SideStats | undefined, key: string) => {
    const v = s?.[key];
    return v === null || v === undefined ? "n.d." : key === "xg" ? v.toFixed(2) : String(v);
  };
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Finestra</th>
            <th className="num">Tiri (C–O)</th>
            <th className="num">In porta (C–O)</th>
            <th className="num">Corner (C–O)</th>
            <th className="num">xG (C–O)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ k, label }) => {
            const win = w[k] as Record<"home" | "away", SideStats> | null;
            return (
              <tr key={k}>
                <td>{label}</td>
                {win === null ? (
                  <td colSpan={4} className="muted small">non disponibile: lo scanner non ha ancora abbastanza storico di snapshot per questa partita</td>
                ) : (
                  ["shots", "sot", "corners", "xg"].map((s) => (
                    <td key={s} className="num">{cell(win.home, s)} – {cell(win.away, s)}</td>
                  ))
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FormBlock({ name, f }: { name: string; f: TeamForm | null | undefined }) {
  if (!f) return <div className="small muted">{name}: forma non disponibile (non ancora scaricata o quota API insufficiente)</div>;
  const r = (x: number) => (f.matches ? `${Math.round((100 * x) / f.matches)}%` : "—");
  return (
    <div style={{ marginBottom: 10 }}>
      <div><strong>{name}</strong> <span className="form-pills">{f.results.slice(0, 10).map((x, i) => <span key={i}>{x === "W" ? "V" : x === "D" ? "N" : "P"}</span>)}</span></div>
      <div className="small muted">
        Ultime {f.matches}: gol fatti {f.goals_for} ({num(f.goals_for / Math.max(f.matches, 1))}/p), subiti {f.goals_against} ({num(f.goals_against / Math.max(f.matches, 1))}/p) ·
        ultime {f.last5_n}: {f.last5_gf}–{f.last5_ga} · casa {f.home_gf}–{f.home_ga} ({f.home_matches}) · trasferta {f.away_gf}–{f.away_ga} ({f.away_matches})
      </div>
      <div className="small muted">Over 1.5 {r(f.over15)} · Over 2.5 {r(f.over25)} · Over 3.5 {r(f.over35)} · Entrambe a segno {r(f.btts)}</div>
    </div>
  );
}

export default function FixtureDrawer({ id, onClose, tick }: { id: number; onClose: () => void; tick: string | null }) {
  const [d, setD] = useState<FixtureDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    getJSON<FixtureDetail>(`/api/fixtures/${id}`).then((x) => { setD(x); setErr(null); }).catch((e) => setErr(String(e)));
  }, [id, tick]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const f = d?.fixture;
  const tl = (d?.timeline ?? []).filter((t) => t.elapsed !== null);
  const tlMinute = (t: (typeof tl)[number]) => (t.elapsed ?? 0) + (t.extra ?? 0);
  const series = (key: string) => [
    { name: `${f?.home ?? "Casa"}`, color: "var(--home)", points: tl.filter((t) => t.home[key] !== null && t.home[key] !== undefined).map((t) => ({ x: tlMinute(t), y: t.home[key] as number })) },
    { name: `${f?.away ?? "Ospite"}`, color: "var(--away)", points: tl.filter((t) => t.away[key] !== null && t.away[key] !== undefined).map((t) => ({ x: tlMinute(t), y: t.away[key] as number })) },
  ];

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Analisi partita">
        {err && <div className="banner critical">{err}</div>}
        {!d || !f ? (
          <div className="muted">Caricamento…</div>
        ) : (
          <>
            <div className="drawer-head">
              <div style={{ flex: 1 }}>
                <div className="small muted">{f.league_name}{f.country ? ` · ${f.country}` : ""}{f.round ? ` · ${f.round}` : ""}</div>
                <div className="score">{f.home} {f.home_goals}–{f.away_goals} {f.away}</div>
                <div className="muted">{minuteLabel(f.status, f.elapsed, f.extra)}</div>
              </div>
              <button className="close" onClick={onClose}>Chiudi ✕</button>
            </div>
            {d.not_analysable_reason && <div className="banner warning">{d.not_analysable_reason}</div>}
            {d.error && <div className="banner critical">Errore di analisi: {d.error}</div>}

            <div className="grid2">
              <div className="card">
                <h2>Statistiche live</h2>
                {d.stats ? (
                  <>
                    <div className="legend">
                      <span><span className="key" style={{ background: "var(--home)" }} />{f.home}</span>
                      <span><span className="key" style={{ background: "var(--away)" }} />{f.away}</span>
                    </div>
                    {COMPARE.map((k) => (
                      <StatRow key={k} name={STAT_LABELS[k]} h={d.stats!.home[k]} a={d.stats!.away[k]} />
                    ))}
                  </>
                ) : (
                  <div className="empty small">Il provider non fornisce statistiche live per questa partita.</div>
                )}
                <h3>Disponibilità dati</h3>
                <div className="chips">
                  {d.availability.provided.map((k) => <span key={k} className="chip">✓ {STAT_LABELS[k] ?? k}</span>)}
                  {d.availability.missing.map((k) => <span key={k} className="chip missing" title="non disponibile">✗ {STAT_LABELS[k] ?? k}</span>)}
                </div>
                <div className="small muted" style={{ marginTop: 6 }}>
                  Attacchi pericolosi, big chances e xGOT non sono forniti da API-Football: non vengono stimati né simulati.
                </div>
              </div>

              <div className="card">
                <h2>Modello in-play</h2>
                {d.model ? (
                  <>
                    <div className="small muted">{MODEL_NAMES[d.model.goal_model] ?? d.model.goal_model} · minuti residui stimati (incl. recupero) {num(d.model.minutes_left_est, 1)}</div>
                    <div className="metrics">
                      <div className="metric"><div className="k">Gol attesi residui {f.home}</div><div className="v">{num(d.model.exp_goals_home)}</div></div>
                      <div className="metric"><div className="k">Gol attesi residui {f.away}</div><div className="v">{num(d.model.exp_goals_away)}</div></div>
                      <div className="metric"><div className="k">P(almeno un altro gol)</div><div className="v">{pct(d.model.p_more_goals)}</div></div>
                      <div className="metric"><div className="k">P(gol nei prossimi 10')</div><div className="v">{pct(d.model.p_goal_next10)}</div></div>
                    </div>
                    <h3>Prossimo gol</h3>
                    <div className="small">{f.home} {pct(d.model.p_next_home)} · {f.away} {pct(d.model.p_next_away)} · nessuno {pct(d.model.p_next_none)}</div>
                    {d.model.corners_expected_rest !== null && (
                      <div className="small">Corner attesi nel resto della gara: {num(d.model.corners_expected_rest, 1)}</div>
                    )}
                    <h3>Probabilità del modello e quota equa (senza margine)</h3>
                    <table>
                      <thead><tr><th>Mercato</th><th className="num">Prob.</th><th className="num">10–90%</th><th className="num">Quota equa</th></tr></thead>
                      <tbody>
                        {d.model.main_markets.map((m) => (
                          <tr key={m.key}><td>{m.label}</td><td className="num">{pct(m.p_model)}</td><td className="num">{pct(m.p_low, 0)}–{pct(m.p_high, 0)}</td><td className="num">{num(m.fair_odds)}</td></tr>
                        ))}
                        <tr><td>Gol nei prossimi 10'</td><td className="num">{pct(d.model.p_goal_next10)}</td><td className="num">—</td><td className="num">{num(d.model.fair_odds_goal_next10)}</td></tr>
                      </tbody>
                    </table>
                    <div className="small muted" style={{ marginTop: 6 }}>Una quota equa non è un consiglio: senza una quota live verificabile il mercato non viene proposto.</div>
                  </>
                ) : (
                  <div className="empty small">Analisi del modello non disponibile.</div>
                )}
              </div>
            </div>

            <div className="grid2" style={{ marginTop: 16 }}>
              <div className="card">
                <h2>Andamento recente</h2>
                <WindowTable d={d} />
                <h3>Tiri in porta cumulati (snapshot dello scanner)</h3>
                <LineChart series={series("sot")} height={180} step xFormat={(v) => `${Math.round(v)}'`} />
                <h3>Tiri totali cumulati</h3>
                <LineChart series={series("shots")} height={180} step xFormat={(v) => `${Math.round(v)}'`} />
              </div>
              <div className="card">
                <h2>Forma delle squadre</h2>
                <FormBlock name={f.home} f={d.form?.home} />
                <FormBlock name={f.away} f={d.form?.away} />
                <h3>Eventi</h3>
                {d.events.length === 0 ? (
                  <div className="small muted">Nessun evento fornito.</div>
                ) : (
                  <table>
                    <tbody>
                      {d.events.map((e, i) => (
                        <tr key={i}>
                          <td className="num">{e.minute}{e.extra ? `+${e.extra}` : ""}'</td>
                          <td>{e.side === "home" ? f.home : e.side === "away" ? f.away : ""}</td>
                          <td>{e.type} {e.detail ? `· ${e.detail}` : ""}</td>
                          <td className="muted">{e.player}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="card" style={{ marginTop: 16 }}>
              <div className="section-title">
                <h2>Mercati con quota live ({d.evaluations.length})</h2>
                <span className="small muted">tutte le selezioni prezzate, comprese quelle scartate e il motivo</span>
              </div>
              {d.note && <div className="small muted">{d.note}</div>}
              {d.evaluations.length > 0 && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Selezione</th><th className="num">Quota</th><th className="num">P stimata</th><th className="num">P prud.</th>
                        <th className="num">P impl.</th><th className="num">P equa</th><th className="num">EV</th><th className="num">EV prud.</th>
                        <th>Confidenza</th><th>Esito filtri</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.evaluations.map((e) => (
                        <tr key={`${e.key}-${e.source}-${e.bookmaker}`}>
                          <td>{e.label}<div className="small muted">{e.bookmaker ?? e.source}</div></td>
                          <td className="num">{num(e.odds)}</td>
                          <td className="num">{pct(e.p_model)}</td>
                          <td className="num">{pct(e.p_cons)}</td>
                          <td className="num">{pct(e.implied)}</td>
                          <td className="num">{pct(e.p_market_fair)}</td>
                          <td className={`num ${e.ev >= 0 ? "pos" : "neg"}`}>{signedPct(e.ev)}</td>
                          <td className={`num ${e.ev_cons >= 0 ? "pos" : "neg"}`}>{signedPct(e.ev_cons)}</td>
                          <td><ConfidenceBadge label={e.confidence_label} score={e.confidence} /></td>
                          <td className="small">{e.passed ? <strong className="pos">✓ supera tutti i filtri</strong> : e.fail_reasons.join(" · ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
