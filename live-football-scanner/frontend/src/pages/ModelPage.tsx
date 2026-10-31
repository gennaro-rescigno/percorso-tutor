import { useEffect, useState } from "react";
import { getJSON, num, pct } from "../api";
import { CalibrationChart } from "../components/Charts";
import type { CalBin } from "../types";

interface Metric { logloss: number; brier?: number; ece?: number; rps?: number; mean_pred?: number }
interface Report {
  n_origins: number;
  n_matches: number;
  binary: Record<string, { family: string; n: number; base_rate: number } & Record<string, Metric | number | string>>;
  multiclass: Record<string, { n: number } & Record<string, Metric | number>>;
  calibration: Record<string, Record<string, CalBin[]>>;
  by_minute: Record<string, { n: number; base_rate: number } & Record<string, Metric | number>>;
  corners: Record<string, unknown>;
}
interface ModelInfo {
  version: string;
  meta: Record<string, unknown>;
  refs: Record<string, number>;
  mu_goals: number;
  stoppage: Record<string, number[]>;
  validation: { reports: Record<string, Report>; family_margins: Record<string, number>; splits: Record<string, number>; temporal_split_date: string };
  glms: Record<string, { features: string[]; dispersion: number; meta: { n_rows: number; n_matches: number; aic: number; coef_table: { feature: string; coef: number; se: number; z: number }[] } }>;
}

const TARGETS: Record<string, string> = {
  any_more: "Almeno un altro gol",
  over25: "Over 2.5 (finale)",
  btts: "Entrambe segnano",
  home_scores: "La squadra di casa segna ancora",
  goal10: "Gol nei prossimi 10'",
  goal_ht: "Gol prima dell'intervallo",
  goal_2h: "Gol nel 2° tempo",
  home_win: "Vittoria casa",
  draw: "Pareggio",
  away_win: "Vittoria ospite",
  next_home: "Prossimo gol: casa",
  next_away: "Prossimo gol: ospite",
  next_none: "Nessun altro gol",
};
const MODELS = ["baseline", "goals_context", "goals_stats", "goals_xg"];
const MODEL_LABEL: Record<string, string> = {
  baseline: "Baseline (Poisson costante)",
  goals_context: "Contesto",
  goals_stats: "Contesto + tiri",
  goals_xg: "Contesto + tiri + xG",
};
const SPLIT_LABEL: Record<string, string> = {
  val_temporal: "Validazione temporale (stessi campionati, mar–mag 2016)",
  val_cross: "Validazione su altre competizioni (2018–2024)",
};

export default function ModelPage() {
  const [m, setM] = useState<ModelInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [target, setTarget] = useState("any_more");
  const [glm, setGlm] = useState("goals_stats");
  useEffect(() => {
    getJSON<ModelInfo>("/api/model").then(setM).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="banner critical">Modello non disponibile: {err}</div>;
  if (!m) return <div className="muted">Caricamento…</div>;
  const reps = m.validation.reports;
  const splits = Object.keys(reps);
  const meta = m.meta as Record<string, string | string[]>;
  return (
    <>
      <div className="banner">
        <div>
          <strong>Modello {m.version}</strong>
          Intensità di gol per minuto (GLM di Poisson, link log) che dipende da minuto, risultato, espulsioni, forza pre-partita,
          ritmo offensivo cumulato e degli ultimi 10' (tiri, tiri in porta, corner, xG se disponibili). La distribuzione del risultato
          finale si ottiene propagando esattamente una catena di Markov sugli stati di punteggio (nessun rumore Monte Carlo); l'incertezza
          dei parametri è propagata con 200 estrazioni dalla covarianza robusta per partita. Dati: {String(meta.data_source)}.
          Addestramento: {(meta.train_competitions as string[])?.join(", ")} prima del {String(meta.train_before)}
          ({m.validation.splits.train} partite). Validazione su partite mai viste: {m.validation.splits.val_temporal} (temporale) e {m.validation.splits.val_cross} (altre competizioni).
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Validazione fuori campione — log-loss (più basso è meglio)</h2>
        {splits.map((s) => (
          <div key={s} style={{ marginBottom: 14 }}>
            <h3>{SPLIT_LABEL[s] ?? s} · {reps[s].n_matches} partite, {reps[s].n_origins} istanti di previsione</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Evento</th><th className="num">N</th><th className="num">Frequenza</th>{MODELS.map((x) => <th key={x} className="num">{MODEL_LABEL[x]}</th>)}<th className="num">Errore calibrazione (ECE)</th></tr>
                </thead>
                <tbody>
                  {Object.entries(reps[s].binary).map(([t, e]) => (
                    <tr key={t}>
                      <td>{TARGETS[t] ?? t}</td>
                      <td className="num">{e.n}</td>
                      <td className="num">{pct(e.base_rate)}</td>
                      {MODELS.map((x) => <td key={x} className="num">{num((e[x] as Metric).logloss, 4)}</td>)}
                      <td className="num">{pct((e.goals_stats as Metric).ece, 1)}</td>
                    </tr>
                  ))}
                  {Object.entries(reps[s].multiclass).map(([t, e]) => (
                    <tr key={t}>
                      <td>{t === "1x2" ? "Esito finale 1X2 (3 classi)" : "Prossimo gol (3 classi)"}</td>
                      <td className="num">{e.n}</td>
                      <td className="num">—</td>
                      {MODELS.map((x) => <td key={x} className="num">{num((e[x] as Metric)?.logloss, 4)}</td>)}
                      <td className="num">{pct((e.goals_stats as Metric).ece, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      <div className="grid2" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="section-title">
            <h2>Calibrazione fuori campione</h2>
            <select value={target} onChange={(e) => setTarget(e.target.value)} aria-label="Evento">
              {Object.keys(reps[splits[0]]?.calibration?.goals_stats ?? {}).map((t) => <option key={t} value={t}>{TARGETS[t] ?? t}</option>)}
            </select>
          </div>
          <CalibrationChart
            series={splits.map((s, i) => ({
              name: SPLIT_LABEL[s] ?? s,
              color: i === 0 ? "var(--home)" : "var(--away)",
              bins: reps[s].calibration.goals_stats?.[target] ?? [],
            }))}
          />
        </div>
        <div className="card">
          <h2>Margini prudenziali per famiglia di mercato</h2>
          <div className="small muted">Peggior errore di calibrazione osservato in validazione (minimo 1.5 pp). Viene sottratto al 10° percentile della probabilità stimata prima di calcolare l'EV prudenziale.</div>
          <table>
            <tbody>
              {Object.entries(m.validation.family_margins).map(([k, v]) => (
                <tr key={k}><td>{k}</td><td className="num">{(100 * v).toFixed(1)} pp</td></tr>
              ))}
            </tbody>
          </table>
          <h3>Accuratezza per fascia di minuto (almeno un altro gol, contesto + tiri)</h3>
          {splits.map((s) => (
            <table key={s} style={{ marginBottom: 8 }}>
              <thead><tr><th>{SPLIT_LABEL[s] ?? s}</th><th className="num">N</th><th className="num">Osservato</th><th className="num">Stimato medio</th></tr></thead>
              <tbody>
                {Object.entries(reps[s].by_minute).map(([k, r]) => (
                  <tr key={k}><td>{k}'</td><td className="num">{r.n}</td><td className="num">{pct(r.base_rate)}</td><td className="num">{pct((r.goals_stats as Metric).mean_pred)}</td></tr>
                ))}
              </tbody>
            </table>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="section-title">
          <h2>Coefficienti stimati</h2>
          <select value={glm} onChange={(e) => setGlm(e.target.value)} aria-label="Sotto-modello">
            {Object.keys(m.glms).map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div className="small muted">
          {m.glms[glm].meta.n_rows.toLocaleString("it-IT")} righe (minuto × squadra × istante di previsione) da {m.glms[glm].meta.n_matches} partite · errori standard robusti per partita
          {m.glms[glm].dispersion > 0 ? ` · dispersione binomiale negativa ${m.glms[glm].dispersion.toFixed(3)}` : ""}
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Variabile</th><th className="num">Coefficiente</th><th className="num">Errore std.</th><th className="num">z</th><th className="num">Effetto moltiplicativo</th></tr></thead>
            <tbody>
              {m.glms[glm].meta.coef_table.map((c) => (
                <tr key={c.feature}><td><code>{c.feature}</code></td><td className="num">{c.coef.toFixed(3)}</td><td className="num">{c.se.toFixed(3)}</td><td className="num">{c.z.toFixed(1)}</td><td className="num">×{Math.exp(c.coef).toFixed(2)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
