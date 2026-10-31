import { useMemo, useState } from "react";
import { ago, minuteLabel, num, pct, signedPct } from "../api";
import { ProbRange } from "../components/Charts";
import { ConfidenceBadge, MARKET_NAMES, Metric, Tile } from "../components/Common";
import type { LiveState, Opportunity } from "../types";

interface Filters {
  league: string;
  minOdds: number;
  minMinute: number;
  maxMinute: number;
  market: string;
  confidence: string;
}

const DEFAULT_FILTERS: Filters = { league: "", minOdds: 1.75, minMinute: 0, maxMinute: 130, market: "", confidence: "" };

function loadFilters(): Filters {
  try {
    const raw = localStorage.getItem("lfs-filters");
    if (raw) return { ...DEFAULT_FILTERS, ...JSON.parse(raw) };
  } catch {
    /* storage unavailable */
  }
  return DEFAULT_FILTERS;
}

function OpportunityCard({ o, rank, onOpen }: { o: Opportunity; rank: number; onOpen: (id: number) => void }) {
  const f = o.fixture;
  return (
    <div className="opp">
      <div className="opp-head">
        <div className="rank">#{rank}</div>
        <div className="opp-match">
          <div className="teams">
            <a href="#" onClick={(e) => { e.preventDefault(); onOpen(o.fixture_id); }}>
              {f.home} {f.home_goals}–{f.away_goals} {f.away}
            </a>
          </div>
          <div className="meta">
            {minuteLabel(f.status, f.elapsed, f.extra)} · {f.league_name}
            {f.country ? ` (${f.country})` : ""} · {MARKET_NAMES[o.market] ?? o.market}
          </div>
          <div className="opp-pick">{o.label}</div>
          <div style={{ marginTop: 6 }}>
            <ConfidenceBadge label={o.confidence_label} score={o.confidence} />
          </div>
        </div>
        <div className="odds-big">
          {num(o.odds)}
          <small>{o.bookmaker ?? o.source} · rilevata a {num(o.odds_at_detection)}</small>
        </div>
      </div>
      <div className="metrics">
        <Metric k="Probabilità stimata" v={pct(o.p_model)} />
        <Metric k="Prob. prudenziale" v={pct(o.p_cons)} />
        <Metric k="Prob. implicita" v={pct(o.implied)} />
        <Metric k="Prob. equa mercato" v={pct(o.p_market_fair)} />
        <Metric k="EV teorico" v={signedPct(o.ev)} cls={o.ev >= 0 ? "pos" : "neg"} />
        <Metric k="EV prudenziale" v={signedPct(o.ev_cons)} cls={o.ev_cons >= 0 ? "pos" : "neg"} />
        <Metric k="Vantaggio" v={`${o.edge >= 0 ? "+" : ""}${(100 * o.edge).toFixed(1)} pp`} />
      </div>
      <ProbRange low={o.p_low} high={o.p_high} p={o.p_model} implied={o.implied} />
      <div className="small muted">
        Barra: intervallo 10–90% della stima (punto = stima, tacca = probabilità implicita dalla quota)
      </div>
      <details>
        <summary>Motivazioni statistiche ({o.reasons.length}) e fattori di rischio ({o.risks.length})</summary>
        <h3>Motivazioni</h3>
        <ul className="reasons">{o.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
        <h3>Principali fattori di rischio</h3>
        <ul className="reasons">{o.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
        <div className="small muted" style={{ marginTop: 6 }}>
          Modello: {o.model?.goal_model} · gol attesi residui {num((o.model?.exp_goals_home ?? 0) + (o.model?.exp_goals_away ?? 0))} ·
          margine di validazione {(100 * o.margin).toFixed(1)} pp · quota aggiornata {o.odds_age_s !== null ? `${Math.round(o.odds_age_s)}s fa` : "—"}
        </div>
      </details>
    </div>
  );
}

export default function LivePage({ state, now, onOpen }: { state: LiveState; now: number; onOpen: (id: number) => void }) {
  const [filters, setFilters] = useState<Filters>(loadFilters);
  const set = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch };
    setFilters(next);
    try {
      localStorage.setItem("lfs-filters", JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };
  const leagues = useMemo(
    () => Array.from(new Set(state.fixtures.map((f) => f.league_name ?? "?"))).sort(),
    [state.fixtures],
  );
  const markets = useMemo(() => Array.from(new Set(state.opportunities.map((o) => o.market))).sort(), [state.opportunities]);
  const minuteOf = (e: number | null, x: number | null) => (e ?? 0) + (x ?? 0);
  const opps = state.opportunities.filter((o) => {
    const f = o.fixture;
    const m = minuteOf(f.elapsed, f.extra);
    return (
      (!filters.league || f.league_name === filters.league) &&
      o.odds >= Math.max(1.75, filters.minOdds) &&
      m >= filters.minMinute &&
      m <= filters.maxMinute &&
      (!filters.market || o.market === filters.market) &&
      (!filters.confidence || (filters.confidence === "alta" ? o.confidence_label === "alta" : o.confidence_label !== "bassa"))
    );
  });
  const fixtures = state.fixtures.filter((f) => !filters.league || f.league_name === filters.league);
  const af = state.providers.api_football;
  return (
    <>
      <div className="kpis">
        <Tile label="Partite live" value={state.n_live} sub={`${state.fixtures.filter((f) => f.has_stats).length} con statistiche live`} />
        <Tile label="Opportunità attive" value={state.n_opportunities} sub={`quota ≥ ${num(state.filters?.min_odds ?? 1.75)} · EV prudenziale ≥ ${signedPct(state.filters?.min_ev ?? 0.03, 0)}`} />
        <Tile label="Ultimo aggiornamento" value={ago(state.updated_at, now)} sub={`ciclo ogni ${state.providers.scanner.poll_interval_s}s · ${state.providers.scanner.last_cycle_ms ?? "—"} ms`} />
        <Tile label="Richieste API-Football rimaste oggi" value={af.quota?.requests_remaining_day ?? "—"} sub={af.quota?.requests_limit_day ? `su ${af.quota.requests_limit_day}` : "dagli header della risposta"} />
      </div>

      <div className="filters" role="group" aria-label="Filtri">
        <label>
          Campionato
          <select value={filters.league} onChange={(e) => set({ league: e.target.value })}>
            <option value="">Tutti</option>
            {leagues.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </label>
        <label>
          Quota minima
          <input type="number" step="0.05" min="1.75" value={filters.minOdds} onChange={(e) => set({ minOdds: Math.max(1.75, Number(e.target.value) || 1.75) })} />
        </label>
        <label>
          Minuto da
          <input type="number" min="0" max="130" value={filters.minMinute} onChange={(e) => set({ minMinute: Number(e.target.value) || 0 })} />
        </label>
        <label>
          Minuto a
          <input type="number" min="0" max="130" value={filters.maxMinute} onChange={(e) => set({ maxMinute: Number(e.target.value) || 130 })} />
        </label>
        <label>
          Mercato
          <select value={filters.market} onChange={(e) => set({ market: e.target.value })}>
            <option value="">Tutti</option>
            {markets.map((m) => <option key={m} value={m}>{MARKET_NAMES[m] ?? m}</option>)}
          </select>
        </label>
        <label>
          Confidenza
          <select value={filters.confidence} onChange={(e) => set({ confidence: e.target.value })}>
            <option value="">Tutte</option>
            <option value="media">Media o alta</option>
            <option value="alta">Solo alta</option>
          </select>
        </label>
        <button className="btn" onClick={() => set(DEFAULT_FILTERS)}>Azzera filtri</button>
      </div>

      <div className="grid2">
        <div className="card">
          <div className="section-title">
            <h2>Classifica opportunità</h2>
            <span className="small muted">ordinate per EV prudenziale × confidenza</span>
          </div>
          {opps.length === 0 ? (
            <div className="empty">
              <strong>NESSUNA OPPORTUNITÀ CON EDGE STATISTICO SUFFICIENTE.</strong>
              {state.n_opportunities > 0
                ? "Ci sono opportunità attive ma nessuna rispetta i filtri selezionati."
                : "Il sistema non forza selezioni: vengono mostrate solo quote ≥ 1.75 con EV positivo dopo il margine prudenziale e dati completi."}
            </div>
          ) : (
            opps.map((o, i) => <OpportunityCard key={o.id} o={o} rank={i + 1} onOpen={onOpen} />)
          )}
        </div>

        <div>
          <div className="card">
            <h2>Partite live ({fixtures.length})</h2>
            {fixtures.length === 0 ? (
              <div className="empty small">{state.message ?? "Nessuna partita live."}</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Min.</th>
                      <th>Partita</th>
                      <th className="num">P(altro gol)</th>
                      <th className="num">Quote</th>
                      <th className="num">Opp.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fixtures.map((f) => (
                      <tr key={f.id} className="click" onClick={() => onOpen(f.id)}>
                        <td>{minuteLabel(f.status, f.elapsed, f.extra)}</td>
                        <td>
                          <div>{f.home} <strong>{f.home_goals}–{f.away_goals}</strong> {f.away}</div>
                          <div className="small muted">
                            {f.league_name}
                            {!f.has_stats && " · statistiche live non disponibili"}
                            {f.not_analysable_reason ? ` · ${f.not_analysable_reason}` : ""}
                          </div>
                        </td>
                        <td className="num">{pct(f.p_more_goals, 0)}</td>
                        <td className="num">{f.n_quotes ?? 0}</td>
                        <td className="num">{f.n_opportunities ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2>Opportunità non più valide</h2>
            {state.invalidated.length === 0 ? (
              <div className="small muted">Nessuna opportunità invalidata finora.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Selezione</th><th className="num">Quota</th><th>Motivo</th></tr>
                  </thead>
                  <tbody>
                    {state.invalidated.slice(0, 15).map((o) => (
                      <tr key={o.id}>
                        <td>
                          <div>{o.label}</div>
                          <div className="small muted">{o.match} · {ago(o.invalidated_at, now)}</div>
                        </td>
                        <td className="num">{num(o.odds_at_detection)}{o.closing_odds ? ` → ${num(o.closing_odds)}` : ""}</td>
                        <td className="small">{o.reason}{o.result ? ` · esito: ${o.result}` : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
