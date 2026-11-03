import { usePoll } from "../api";
import { Column, DataTable, ErrorBox, Kpi, Status } from "../components/ui";
import { fmtNum, fmtPctPlain, fmtTime } from "../format";

const LABEL: Record<string, string> = {
  hit_2x_first: "raddoppia prima di dimezzarsi (4 h)",
  rug_60m: "crollo ≥ 80% entro 60 min",
};

function AucCell({ v }: { v: any }) {
  if (!v) return <span className="muted">dati insufficienti</span>;
  const ci = v.ci ? ` [${v.ci[0].toFixed(2)}–${v.ci[1].toFixed(2)}]` : "";
  return <span className={v.informative ? "" : "muted"}>{v.auc?.toFixed(3)}{ci}{v.informative ? " ✓" : ""}</span>;
}

const VARIANT: Record<string, string> = {
  x_copy_3s: "copia i migliori, 3 s di ritardo", x_copy_10s: "copia i migliori, 10 s di ritardo",
  x_copy_ctrl: "controllo: wallet a caso, 3 s",
};

function CopyExperiment({ c }: { c: any }) {
  if (!c) return null;
  const rep = c.report?.variants ?? {};
  const live = Object.fromEntries((c.live ?? []).map((v: any) => [v.variant, v]));
  const pct = (v: number | null | undefined) => v == null || Number.isNaN(v) ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
  const variants = Array.from(new Set([...Object.keys(VARIANT), ...Object.keys(rep)]));
  return (
    <div className="card section">
      <h2>Esperimento: copiare i wallet che guadagnano davvero</h2>
      <div className="note">
        Il bot misura dallo stream gratuito il risultato reale di ogni wallet sulle curve pump.fun (perdite incluse, anche quelle
        tenute in portafoglio; esclusi creatori, sniper del primo blocco, chi vende token ricevuti da altri). Ogni ora sceglie i
        50 migliori degli <b>ultimi 3 giorni</b> e simula di copiarne gli acquisti <b>da quel momento in poi</b>, con qualche secondo
        di ritardo, 0,1 SOL a copia, commissioni incluse. Un gruppo di wallet a caso fa da controllo: se i "migliori" non lo battono,
        era solo fortuna. Nessuna operazione reale.
      </div>
      <table><thead><tr><th>Variante</th><th className="num">Copie chiuse</th><th className="num">Media</th><th className="num">IC 95%</th>
        <th className="num">Mediana</th><th className="num">Vincenti</th><th className="num">P/L (SOL)</th><th className="num">Aperte ora</th><th>Verdetto</th></tr></thead>
        <tbody>{variants.map((v) => {
          const r = rep[v] ?? {}; const l = live[v] ?? {};
          return (
            <tr key={v}><td>{VARIANT[v] ?? v}</td><td className="num">{fmtNum(r.n ?? 0)}</td><td className="num">{pct(r.mean_pct)}</td>
              <td className="num">{r.ci_pct ? `${pct(r.ci_pct[0])} / ${pct(r.ci_pct[1])}` : "–"}</td><td className="num">{pct(r.median_pct)}</td>
              <td className="num">{r.win_rate != null ? fmtPctPlain(r.win_rate) : "–"}</td><td className="num">{r.pnl_sol ?? "–"}</td>
              <td className="num">{fmtNum(l.open ?? 0)}</td><td>{r.verdict ?? "in attesa delle prime copie"}</td></tr>
          );
        })}</tbody></table>
      {c.leaders && (
        <div className="muted">Scelta del {fmtTime(c.leaders.chosen_at)}: {fmtNum(c.leaders.wallets_measured)} wallet misurati,
          {" "}{fmtNum(c.leaders.eligible)} con attività copiabile, {(c.leaders.leaders ?? []).length} scelti
          {(c.leaders.leaders ?? []).length > 0 && ` (il primo: ${c.leaders.leaders[0].n} posizioni, ${fmtPctPlain(c.leaders.leaders[0].win_rate)} vincenti, ${c.leaders.leaders[0].pnl_sol} SOL)`}.
          {c.ledger && ` Registro: ${fmtNum(c.ledger.positions_closed)} posizioni chiuse, ${fmtNum(c.ledger.marked_dead)} rimaste in mano su token morti, ${fmtNum(c.ledger.transfer_sells)} vendite di token ricevuti da altri.`}</div>
      )}
    </div>
  );
}

function RulesLab({ lab }: { lab: any }) {
  if (!lab) return null;
  const pct = (v: number | null) => v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
  return (
    <div className="card section">
      <h2>Laboratorio delle regole (fissate il {fmtTime(lab.registered_at)}, provate su ogni lancio)</h2>
      <div className="note">{lab.note} Costi inclusi: latenza {(lab.costs?.latency * 100).toFixed(0)}%, commissione {(lab.costs?.fee_per_side * 100).toFixed(2)}% per lato,
        priority fee {(lab.costs?.priority_round_trip * 100).toFixed(0)}%, stop riempito a {lab.costs?.stop_fill_pct}%. Nessuna regola cambia il bot da sola.</div>
      <table><thead><tr><th>Regola</th><th>Uscita</th><th className="num">Operazioni fuori campione</th><th className="num">Media</th><th className="num">IC 95%</th>
        <th className="num">Vincenti</th><th className="num">Media in campione (solo informativa)</th><th>Verdetto</th></tr></thead>
        <tbody>{(lab.results ?? []).map((r: any) => (
          <tr key={r.rule + r.exit}><td><b>{r.rule}</b> <span className="muted">{r.description}</span></td><td title={lab.exits?.[r.exit]}>{r.exit}</td>
            <td className="num">{fmtNum(r.n_oos)}</td><td className="num">{pct(r.mean_oos_pct)}</td>
            <td className="num">{r.ci_oos ? `${pct(r.ci_oos[0])} / ${pct(r.ci_oos[1])}` : "–"}</td>
            <td className="num">{r.win_oos != null ? fmtPctPlain(r.win_oos) : "–"}</td>
            <td className="num muted">{pct(r.mean_in_sample_pct)} (n={fmtNum(r.n_in_sample)})</td>
            <td><Status level={r.verdict.startsWith("promettente") ? "good" : r.verdict === "non funziona" ? "critical" : "warning"} label={r.verdict} /></td></tr>
        ))}</tbody></table>
      <div className="muted">{Object.entries(lab.exits ?? {}).map(([k, v]: any) => `${k}: ${v}`).join(" · ")}</div>
    </div>
  );
}

function EventStudy({ ev }: { ev: any }) {
  if (!ev) return <div className="card section"><h2>Cosa succede dopo ogni evento</h2><div className="muted">Lo studio parte dopo la prima ora di diario.</div></div>;
  const pct = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
  const rows = [...(ev.events ?? [])];
  const base = Object.entries(ev.baseline ?? {}) as [string, any][];
  return (
    <div className="card section">
      <h2>Cosa succede dopo ogni evento (ultimi {ev.days} giorni, finestra {ev.window_min} min)</h2>
      <div className="note">{ev.note} Il "momento qualsiasi" è la stessa misura presa a 1, 5 o 15 minuti dal lancio, senza nessun evento: serve da confronto.</div>
      <table><thead><tr><th>Evento</th><th className="num">Casi</th><th className="num">Età mediana</th><th className="num">Variazione mediana a 60 min</th>
        <th className="num">Tocca +100%</th><th className="num">Tocca −50%</th><th className="num">Si diploma entro 60 min</th><th>Confronto</th></tr></thead>
        <tbody>
          {rows.map((r: any) => (
            <tr key={r.event}><td>{r.event}</td><td className="num">{fmtNum(r.n)}</td><td className="num">{r.age_median_min} min</td>
              <td className="num">{pct(r.end_median_pct)}</td><td className="num">{fmtPctPlain(r.p_up_100)}</td><td className="num">{fmtPctPlain(r.p_down_50)}</td>
              <td className="num">{fmtPctPlain(r.p_migrated)}</td><td className="muted">{r.baseline}</td></tr>
          ))}
          {base.map(([h, b]) => (
            <tr key={h} className="muted"><td>momento qualsiasi ({h})</td><td className="num">{fmtNum(b.n)}</td><td className="num">{b.age_median_min} min</td>
              <td className="num">{pct(b.end_median_pct)}</td><td className="num">{fmtPctPlain(b.p_up_100)}</td><td className="num">{fmtPctPlain(b.p_down_50)}</td>
              <td className="num">{fmtPctPlain(b.p_migrated)}</td><td></td></tr>
          ))}
        </tbody></table>
      {(ev.small_groups ?? []).length > 0 && <div className="muted">Ancora pochi casi (meno di 30): {ev.small_groups.join(", ")}</div>}
      {(ev.listed ?? []).length > 0 && (
        <>
          <h3>Token già quotati (dai controlli dello scanner)</h3>
          <table><thead><tr><th>Evento</th><th className="num">Casi</th><th className="num">Variazione mediana a 60 min</th>
            <th className="num">Tocca +100%</th><th className="num">Tocca −50%</th></tr></thead>
            <tbody>{ev.listed.map((r: any) => (
              <tr key={r.event}><td>{r.event}</td><td className="num">{fmtNum(r.n)}</td><td className="num">{pct(r.end_median_pct)}</td>
                <td className="num">{fmtPctPlain(r.p_up_100)}</td><td className="num">{fmtPctPlain(r.p_down_50)}</td></tr>
            ))}</tbody></table>
        </>
      )}
      <div className="muted">Aggiornato il {fmtTime(ev.generated_at)} · esclusi per interruzioni dello stream: {fmtNum(ev.skipped?.stream_gap)}</div>
    </div>
  );
}

export default function Research() {
  const { data, error } = usePoll<any>("/research", 120000);
  const r = data?.report;
  const d = data?.dataset ?? {};
  const cols: Column<any>[] = [
    { key: "feature", label: "Caratteristica", render: (x) => <span className="mono">{x.feature}</span> },
    { key: "n", label: "Osservazioni", num: true },
    { key: "hit_2x_first", label: "AUC vs raddoppio", num: true, value: (x) => x.hit_2x_first?.auc, render: (x) => <AucCell v={x.hit_2x_first} /> },
    { key: "rug_60m", label: "AUC vs crollo", num: true, value: (x) => x.rug_60m?.auc, render: (x) => <AucCell v={x.rug_60m} /> },
  ];
  const rules = Object.entries(r?.shadow_rules ?? {}) as [string, any][];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Ricerca – cosa dicono i dati reali</h1>
      <ErrorBox error={error} />
      <div className="note">
        Ogni lancio pump.fun visto sulla blockchain viene fotografato a 1, 5 e 15 minuti dalla creazione (solo dati disponibili
        in quel momento), poi dopo 4 ore si registra cosa è successo davvero. Qui si misura quali caratteristiche anticipano
        un buon esito o un crollo. <b>AUC 0,5 = nessuna informazione</b>; una caratteristica è segnata ✓ solo se
        l'intervallo di confidenza al 95% esclude 0,5. Nessuna regola viene cambiata automaticamente.
      </div>
      <div className="grid kpis section">
        <Kpi label="Lanci registrati" value={fmtNum(d.launches)} sub={`ultime 24 h: ${fmtNum(d.launches_24h)}`} />
        <Kpi label="Istantanee feature" value={fmtNum(d.feature_snapshots)} sub={`con esito: ${fmtNum(d.labeled)}`} />
        <Kpi label="Operazioni iniziali salvate" value={fmtNum(d.early_trades)} />
        <Kpi label="Wallet analizzati" value={fmtNum(d.wallet_profiles)} />
        <Kpi label="Candele dallo stream" value={fmtNum(d.stream_candles)} />
        <Kpi label="Eventi nel diario" value={fmtNum(d.token_events)} sub="fatti on-chain di ogni lancio" />
      </div>
      <CopyExperiment c={data?.copy} />
      <RulesLab lab={data?.rules_lab} />
      <EventStudy ev={data?.event_study} />
      {!r && <div className="warn-box">Il primo rapporto viene calcolato dopo l'avvio e poi ogni ora: servono almeno 4 ore di raccolta per i primi esiti.</div>}
      {r && (
        <>
          <div className="card section">
            <h2>Verdetto</h2>
            <p><b>{r.verdict}</b></p>
            <div className="muted">Rapporto del {fmtTime(r.generated_at)} · orizzonte {r.horizon} · osservazioni usabili {fmtNum(r.rows_usable)} su {fmtNum(r.rows_total)}
              {" "}(minimo per conclusioni: {r.min_rows} osservazioni e {r.min_positives} casi positivi)</div>
            {r.base_rates && (
              <table style={{ marginTop: 8 }}><tbody>
                {Object.entries(r.base_rates).map(([k, v]: any) => (
                  <tr key={k}><td>{LABEL[k] ?? k}</td><td className="num">{fmtNum(v.positives)} casi</td><td className="num">{fmtPctPlain(v.rate)}</td></tr>
                ))}
              </tbody></table>
            )}
          </div>
          <div className="card section">
            <h2>Gli indici di rischio e opportunità funzionano?</h2>
            <table><tbody>
              {Object.entries(r.indices ?? {}).map(([k, v]: any) => (
                <tr key={k}><td>{k}</td><td>vs {LABEL[v.target] ?? v.target}</td>
                  <td className="num">{v.auc != null ? `AUC ${v.auc.toFixed(3)}${v.ci ? ` [${v.ci[0].toFixed(2)}–${v.ci[1].toFixed(2)}]` : ""}` : v.verdict}</td>
                  <td className="num muted">n = {fmtNum(v.n)}</td></tr>
              ))}
            </tbody></table>
            <div className="note">{data?.index_note}</div>
          </div>
          {r.walk_forward && (
            <div className="card section">
              <h2>Test fuori campione (walk-forward)</h2>
              <table><tbody>
                {Object.entries(r.walk_forward).map(([k, v]: any) => (
                  <tr key={k}><td>{LABEL[k] ?? k}</td>
                    <td><Status level={v.verdict === "informativo fuori campione" ? "good" : "warning"} label={v.verdict} /></td>
                    <td className="num">{v.mean_auc != null ? `AUC media ${v.mean_auc.toFixed(3)}` : ""}</td>
                    <td className="num muted">{v.beats_base_rate_folds ? `batte il tasso base in ${v.beats_base_rate_folds} periodi` : ""}</td></tr>
                ))}
              </tbody></table>
              <div className="note">Il modello è addestrato solo sul passato e provato sul periodo successivo: se non batte il tasso base, non serve.</div>
            </div>
          )}
          {rules.length > 0 && (
            <div className="card section">
              <h2>Regole shadow sui dati reali</h2>
              <table><thead><tr><th>Regola</th><th className="num">Scatta</th><th className="num">Crolli se scatta</th><th className="num">Crolli altrimenti</th><th className="num">Raddoppi se scatta</th><th className="num">Raddoppi altrimenti</th></tr></thead>
                <tbody>{rules.map(([k, v]) => (
                  <tr key={k}><td className="mono">{k}</td><td className="num">{fmtNum(v.fires)}</td>
                    <td className="num">{fmtPctPlain(v.rug_rate_if_fires)}</td><td className="num">{fmtPctPlain(v.rug_rate_otherwise)}</td>
                    <td className="num">{fmtPctPlain(v.win_rate_if_fires)}</td><td className="num">{fmtPctPlain(v.win_rate_otherwise)}</td></tr>
                ))}</tbody></table>
            </div>
          )}
          <div className="card section">
            <h2>Caratteristiche una per una</h2>
            <DataTable rows={r.features ?? []} columns={cols} initialSort={{ key: "hit_2x_first", desc: true }} empty="Nessuna caratteristica con dati sufficienti" />
          </div>
        </>
      )}
    </>
  );
}
