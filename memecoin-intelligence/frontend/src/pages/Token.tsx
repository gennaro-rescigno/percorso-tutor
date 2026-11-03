import { useParams } from "react-router-dom";
import { usePoll } from "../api";
import { TimeLine } from "../components/charts";
import { OnchainSection } from "../components/onchain";
import { ErrorBox, Kpi, ScoreBars } from "../components/ui";
import { fmtNum, fmtPct, fmtPctPlain, fmtPrice, fmtTime, fmtUsd } from "../format";

export default function TokenPage() {
  const { address } = useParams();
  const { data, error } = usePoll<any>(`/tokens/${address}`, 30000);
  const t = data?.token;
  const s = data?.snapshot ?? {};
  const sc = data?.score;
  const candles = (data?.candles ?? []).map((c: any) => ({ ts: c.ts, close: c.c, volume: c.v }));
  const priceSeries = candles.length ? candles : (data?.history ?? []).map((h: any) => ({ ts: h.ts, close: h.price_sol }));
  const wash = s.social_metrics?.wash;
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>{t?.symbol ?? "Token"} <span className="muted mono">{address}</span></h1>
      <ErrorBox error={error} />
      <div className="grid kpis">
        <Kpi label="Score" value={sc ? `${Math.round(sc.total)}/100` : "n/d"} sub={sc ? `${sc.label} · copertura ${fmtPctPlain(sc.coverage, 0)}` : undefined} />
        <Kpi label="Prezzo" value={fmtPrice(s.price_usd)} sub={s.price_native ? `${fmtPrice(s.price_native)} SOL` : undefined} />
        <Kpi label="Market cap" value={fmtUsd(s.market_cap_usd ?? s.fdv_usd)} sub={`FDV ${fmtUsd(s.fdv_usd)}`} />
        <Kpi label="Liquidità" value={fmtUsd(s.liquidity_usd)} />
        <Kpi label="Volume 1h / 24h" value={fmtUsd(s.volume_usd?.h1)} sub={fmtUsd(s.volume_usd?.h24)} />
        <Kpi label="Holder" value={fmtNum(s.holders_count)} sub={`top10 ${s.top10_pct != null ? fmtPctPlain(s.top10_pct / 100) : "n/d"}`} />
      </div>
      {sc?.excluded && (
        <div className="warn-box section">⛔ Escluso dai filtri: {sc.exclusion_reasons.join("; ")}</div>
      )}
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Prezzo (SOL)</h2>
          <TimeLine data={priceSeries} x="ts" y="close" name="Prezzo" fmt={(v) => fmtPrice(v)} />
        </div>
        <div className="card">
          <h2>Volume per minuto ({data?.candles?.[0]?.unit ?? "USD"})</h2>
          <TimeLine data={candles} x="ts" y="volume" name="Volume" fmt={(v) => (data?.candles?.[0]?.unit === "SOL" ? `${fmtNum(v, 2)} SOL` : fmtUsd(v))} area />
        </div>
        <div className="card">
          <h2>Liquidità (USD)</h2>
          <TimeLine data={data?.history ?? []} x="ts" y="liquidity_usd" name="Liquidità" fmt={(v) => fmtUsd(v)} />
        </div>
        <div className="card">
          <h2>Market cap (USD)</h2>
          <TimeLine data={data?.history ?? []} x="ts" y="mcap_usd" name="Market cap" fmt={(v) => fmtUsd(v)} />
        </div>
      </div>
      <OnchainSection snap={s} launch={data?.launch} features={data?.feature_snapshots ?? []} />
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Score dettagliato</h2>
          {sc ? <ScoreBars categories={sc.categories} /> : <div className="muted">n/d</div>}
          {sc && (
            <>
              <h3>Perché questo punteggio</h3>
              <ul className="list">{sc.explanations.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul>
            </>
          )}
        </div>
        <div className="card">
          <h2>Rischi individuati</h2>
          <ul className="list">{(sc?.risks?.length ? sc.risks : ["nessun rischio specifico rilevato"]).map((r: string, i: number) => <li key={i}>{r}</li>)}</ul>
          <h3>Distribuzione holder e wallet</h3>
          <table><tbody>
            <tr><td>Top 1 holder</td><td>{s.top1_pct != null ? fmtPctPlain(s.top1_pct / 100) : "n/d"}</td></tr>
            <tr><td>Top 10 holder (esclusi pool)</td><td>{s.top10_pct != null ? fmtPctPlain(s.top10_pct / 100) : "n/d"}</td></tr>
            <tr><td>Deployer</td><td>{s.dev_pct != null ? fmtPctPlain(s.dev_pct / 100) : "n/d"} <span className="mono muted">{t?.deployer ?? ""}</span></td></tr>
            <tr><td>Cluster insider</td><td>{s.insider_cluster_pct != null ? fmtPctPlain(s.insider_cluster_pct / 100) : "n/d"}</td></tr>
            <tr><td>Wash score</td><td>{s.wash_score != null ? s.wash_score.toFixed(2) : "n/d"}{wash ? ` · ${wash.unique_traders} trader, ${wash.trades_per_trader.toFixed(1)} tx/trader` : ""}</td></tr>
            <tr><td>Mint / freeze authority</td><td>{s.mint_authority_revoked == null ? "n/d" : s.mint_authority_revoked ? "revocata" : "ATTIVA"} / {s.freeze_authority_revoked == null ? "n/d" : s.freeze_authority_revoked ? "revocata" : "ATTIVA"}</td></tr>
            <tr><td>Vendibilità (quote reale)</td><td>{s.sell_route_ok == null ? "n/d" : s.sell_route_ok ? `ok, impatto ${s.sell_impact_pct?.toFixed(2)}%` : "NESSUNA ROTTA"}</td></tr>
          </tbody></table>
          <h3>Community e sentiment</h3>
          <table><tbody>
            {Object.entries(s.socials ?? {}).map(([k, v]: any) => <tr key={k}><td>{k}</td><td><a href={v} target="_blank" rel="noreferrer noopener">{String(v).slice(0, 50)}</a></td></tr>)}
            <tr><td>Boost DexScreener attivi</td><td>{s.boosts_active ?? "n/d"} <span className="muted">(promozione a pagamento)</span></td></tr>
            <tr><td>Reddit 24h</td><td>{s.social_metrics?.reddit ? `${s.social_metrics.reddit.posts} post, ${s.social_metrics.reddit.unique_authors} autori` : "n/d"}</td></tr>
            <tr><td>X / Twitter</td><td className="muted">non disponibile (API a pagamento)</td></tr>
          </tbody></table>
        </div>
      </div>
      <div className="card section">
        <h2>Segnali su questo token</h2>
        {(data?.signals ?? []).length === 0 && <div className="muted">Nessun segnale generato</div>}
        {(data?.signals ?? []).map((g: any) => (
          <div key={g.id} style={{ marginBottom: 10 }}>
            <b>{fmtTime(g.created_at)} · strategia {g.strategy} · score {Math.round(g.score)} · {g.status}</b>
            {g.rejection && <div className="muted">non eseguito: {g.rejection}</div>}
            <ul className="list">{g.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul>
            {g.price_1h && <div className="muted">dopo 1h: {fmtPct(g.price_1h / g.reference_price - 1)} · max 24h {fmtPct(g.max_gain_24h)}</div>}
          </div>
        ))}
      </div>
    </>
  );
}
