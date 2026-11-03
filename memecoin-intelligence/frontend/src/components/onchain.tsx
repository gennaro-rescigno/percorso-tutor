import { Status } from "./ui";
import { fmtNum, fmtPctPlain, fmtTime } from "../format";

const lvl = (x: number | null | undefined) =>
  x == null ? <span className="muted">n/d</span>
    : x >= 1 ? <Status level="critical" label="rischio" /> : x >= 0.5 ? <Status level="warning" label="attenzione" /> : <Status level="good" label="ok" />;

function IndexCard({ title, idx, positive }: { title: string; idx: any; positive?: boolean }) {
  if (!idx) return <div className="card"><h3>{title}</h3><div className="muted">non ancora calcolato</div></div>;
  return (
    <div className="card">
      <h3>{title}: {idx.value == null ? "non determinabile" : `${Math.round(idx.value)}/100`}</h3>
      <div className="muted">copertura dati {fmtPctPlain(idx.coverage, 0)} · {idx.note}</div>
      {idx.blocking?.length > 0 && <div className="warn-box">⛔ bloccante: {idx.blocking.join(", ")}</div>}
      {idx.shadow_hits?.length > 0 && <div className="note">regole shadow che scatterebbero: {idx.shadow_hits.join(", ")}</div>}
      <table><tbody>
        {(idx.factors ?? []).map((f: any) => (
          <tr key={f.name}>
            <td>{f.name}</td>
            <td className="num">{f.value == null ? "n/d" : typeof f.value === "boolean" ? (f.value ? "sì" : "no") : typeof f.value === "number" ? fmtNum(f.value, f.value < 10 ? 2 : 0) : String(f.value)}</td>
            <td>{positive ? (f.level == null ? <span className="muted">n/d</span> : f.level >= 1 ? <Status level="good" label="forte" /> : f.level >= 0.5 ? <Status level="warning" label="media" /> : <Status level="critical" label="debole" />) : lvl(f.level)}</td>
            <td className="muted">{f.note}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  );
}

export function OnchainSection({ snap, launch, features }: { snap: any; launch: any; features: any[] }) {
  const oc = snap?.onchain ?? {};
  const f = oc.curve;
  const w = oc.wallets;
  const dep = oc.deployer;
  const findings: any[] = snap?.onchain_findings ?? [];
  return (
    <>
      <div className="grid cols-2 section">
        <IndexCard title="Indice di rischio" idx={oc.risk} />
        <IndexCard title="Indice di opportunità" idx={oc.opportunity} positive />
      </div>
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Sicurezza letta dalla blockchain</h2>
          {snap?.sources?.onchain_security ? (
            findings.length === 0 ? <div><Status level="good" label="nessun problema nel contratto" /></div> : (
              <table><tbody>{findings.map((x) => (
                <tr key={x.code}><td>{x.blocking ? <Status level="critical" label="bloccante" /> : <Status level="warning" label={x.severity} />}</td>
                  <td className="mono">{x.code}</td><td>{x.message}</td></tr>
              ))}</tbody></table>
            )
          ) : <div className="muted">non ancora verificato</div>}
          <table style={{ marginTop: 8 }}><tbody>
            <tr><td>Programma del token</td><td className="mono muted">{snap?.token_program ?? "n/d"}</td></tr>
            <tr><td>Metadati modificabili</td><td>{snap?.metadata_mutable == null ? "n/d" : snap.metadata_mutable ? "sì" : "no (immutabili)"}</td></tr>
            <tr><td>Curva "mayhem"</td><td>{snap?.mayhem == null ? "n/d" : snap.mayhem ? "sì (prezzo mosso da un agente)" : "no"}</td></tr>
            <tr><td>Vendita simulata on-chain</td><td>{snap?.sell_sim_ok == null ? `non verificata${snap?.sell_sim_detail ? ` (${snap.sell_sim_detail})` : ""}` : snap.sell_sim_ok ? `ok – ${snap.sell_sim_detail}` : `FALLITA – ${snap.sell_sim_detail}`}</td></tr>
            <tr><td>Curva completata</td><td>{snap?.bonding_progress_pct != null ? `${fmtNum(snap.bonding_progress_pct, 1)}%` : "n/d"}</td></tr>
          </tbody></table>
        </div>
        <div className="card">
          <h2>Primi minuti sulla curva (stream)</h2>
          {!f ? <div className="muted">lancio non osservato dallo stream</div> : (
            <>
              {!f.complete && <div className="warn-box">Dati incompleti (stream interrotto nella finestra): non usati come segnale.</div>}
              <table><tbody>
                <tr><td>Età</td><td>{fmtNum(f.age_s / 60, 1)} min · {fmtNum(f.n_trades)} operazioni</td></tr>
                <tr><td>Acquirenti unici / venditori</td><td>{fmtNum(f.unique_buyers)} / {fmtNum(f.unique_sellers)}</td></tr>
                <tr><td>SOL comprati / venduti</td><td>{fmtNum(f.buy_sol, 2)} / {fmtNum(f.sell_sol, 2)} (pressione {fmtPctPlain(f.buy_pressure)})</td></tr>
                <tr><td>Acquisti nel blocco di creazione</td><td>{fmtNum(f.same_slot_buyers)} wallet · {fmtNum(f.same_slot_pct, 2)}% della supply</td></tr>
                <tr><td>Sniper (primi 3 slot)</td><td>{fmtNum(f.sniper_buyers)} wallet · {fmtNum(f.sniper_pct, 2)}%</td></tr>
                <tr><td>Creatore</td><td>comprato {fmtNum(f.creator_buy_sol, 2)} SOL · {f.creator_sold ? "HA VENDUTO" : "non ha venduto"} · detiene {fmtNum(f.creator_net_pct, 2)}%</td></tr>
                <tr><td>Top 10 holder</td><td>{fmtNum(f.top10_net_pct, 2)}% · flipper {fmtPctPlain(f.flipper_share)}</td></tr>
                <tr><td>Ultimo minuto</td><td>{fmtNum(f.buyers_last_60s)} acquirenti</td></tr>
              </tbody></table>
            </>
          )}
        </div>
      </div>
      <div className="grid cols-2 section">
        <div className="card">
          <h2>Wallet dei primi acquirenti</h2>
          {!w ? <div className="muted">non ancora analizzati (budget RPC gratuito limitato: si analizzano i candidati migliori)</div> : (
            <>
              <table><tbody>
                <tr><td>Analizzati</td><td>{fmtNum(w.profiled)} su {fmtNum(w.early_buyers)} (copertura {fmtPctPlain(w.coverage, 0)})</td></tr>
                <tr><td>Wallet coordinati</td><td>{fmtNum(w.clustered_wallets)} in cluster · {fmtNum(w.creator_linked_wallets)} finanziati dal creatore · {fmtNum(w.block0_wallets)} nel blocco 0</td></tr>
                <tr><td>Supply coordinata</td><td>{fmtNum(w.coordinated_pct, 2)}%</td></tr>
                <tr><td>Acquirenti indipendenti</td><td>{fmtNum(w.independent_buyers)}</td></tr>
                <tr><td>Wallet nuovi (&lt; 3 giorni)</td><td>{fmtNum(w.fresh_wallets)} ({fmtPctPlain(w.fresh_share)})</td></tr>
              </tbody></table>
              {(w.evidence ?? []).length > 0 && (
                <><h3>Prove dei collegamenti</h3><ul className="list">{w.evidence.map((e: any, i: number) => <li key={i}><span className="mono">{e.wallet}</span>: {e.link}</li>)}</ul></>
              )}
              <div className="note">Solo collegamenti di fatto (stesso finanziatore, finanziato dal creatore). Gli exchange e i servizi molto attivi vengono ignorati.</div>
            </>
          )}
        </div>
        <div className="card">
          <h2>Storico del creatore</h2>
          {!dep ? <div className="muted">n/d</div> : (
            <table><tbody>
              <tr><td>Lanci negli ultimi 30 giorni</td><td>{fmtNum(dep.launches_30d)} (24 h: {fmtNum(dep.launches_24h)})</td></tr>
              <tr><td>Migrati</td><td>{fmtNum(dep.migrated)}</td></tr>
              <tr><td>Crollati</td><td>{dep.rug_share == null ? "n/d" : fmtPctPlain(dep.rug_share)} su {fmtNum(dep.labeled)} con esito</td></tr>
              <tr><td>Storico disponibile</td><td>{fmtNum(dep.observed_days, 1)} giorni di raccolta</td></tr>
            </tbody></table>
          )}
          {launch && <div className="note">Lancio visto il {fmtTime(launch.created_at)} (fonte {launch.source}){launch.complete_at ? ` · migrato il ${fmtTime(launch.complete_at)}` : ""}.</div>}
          {features.length > 0 && (
            <>
              <h3>Istantanee del feature store</h3>
              <table><tbody>{features.map((x) => (
                <tr key={x.horizon}><td>{x.horizon}</td><td>rischio {fmtNum(x.risk?.value)} · opportunità {fmtNum(x.opportunity?.value)}</td>
                  <td className="muted">{x.labels ? `esito: ${x.labels.first_passage ?? "n/d"}, max 60 min ${fmtNum(x.labels.ret_max_60m, 0)}%` : "esito tra 4 h"}</td></tr>
              ))}</tbody></table>
            </>
          )}
        </div>
      </div>
    </>
  );
}

const JOURNAL_LABEL: Record<string, string> = {
  create: "lancio", dev_buy: "il creatore compra", dev_sell: "il creatore vende", block0: "acquirenti nel blocco 0",
  whale_buy: "acquisto grande", whale_sell: "vendita grande", wash_atomic: "wash trade atomico (stesso wallet compra e vende)",
  reserve: "riserva della curva", drawdown: "calo dal massimo", volume_spike: "picco di acquisti", complete: "diploma (migrazione)",
  dead: "30 minuti senza scambi", copy: "nome già usato da un lancio precedente",
  listed: "visto per la prima volta dallo scanner", price_jump: "prezzo in forte salita", price_drop: "prezzo in forte calo",
  liquidity_drop: "liquidità ritirata", boost_on: "promozione DexScreener attivata (a pagamento)",
  migrated: "migrazione vista dallo scanner", holders_jump: "holder in forte aumento",
};

function journalValue(e: any): string {
  const d = e.detail ?? {};
  switch (e.kind) {
    case "dev_buy": case "whale_buy": case "whale_sell": return `${e.value?.toFixed(3)} SOL`;
    case "dev_sell": return `${e.value?.toFixed(3)} SOL${d.sold_all ? " · TUTTO" : d.share_of_holding != null ? ` · ${(d.share_of_holding * 100).toFixed(0)}% di quanto aveva` : ""}`;
    case "block0": return `${e.value} wallet · ${d.sol} SOL · ${d.supply_pct}% della supply`;
    case "reserve": return `≥ ${e.value} SOL (prezzo ×${d.multiple} dal lancio)`;
    case "drawdown": return `−${e.value}% (picco a ${d.peak_reserve_sol} SOL)`;
    case "volume_spike": return `${e.value} acquisti in 60 s da ${d.wallets} wallet`;
    case "complete": return `dopo ${Math.round((e.value ?? 0) / 60)} min`;
    case "dead": return e.value != null ? `ultimo prezzo = ${(e.value * 100).toFixed(0)}% del massimo` : "";
    case "copy": return `${e.value} lanci precedenti con lo stesso nome`;
    case "create": return d.mayhem ? "modalità mayhem" : `metadati: ${d.uri_kind}${d.quote && d.quote !== "SOL" ? ` · quotato in ${d.quote}… (non SOL)` : ""}`;
    case "listed": return `liquidità ${e.value != null ? Math.round(e.value).toLocaleString("it-IT") + " $" : "n/d"} · ${d.dex ?? ""}`;
    case "price_jump": case "price_drop": return `${e.value > 0 ? "+" : ""}${e.value}% tra due controlli`;
    case "liquidity_drop": return `${e.value}% (da ${d.from_usd} $ a ${d.to_usd} $)`;
    case "boost_on": return `${e.value} boost attivi`;
    case "holders_jump": return `da ${d.from} a ${e.value} holder`;
    default: return e.value != null ? String(e.value) : "";
  }
}

export function JournalSection({ events }: { events: any[] }) {
  if (!events?.length) return null;
  const age = (s: number | null) => s == null ? "" : s < 90 ? `${Math.round(s)} s` : `${(s / 60).toFixed(1)} min`;
  return (
    <div className="card section">
      <h2>Diario del token (fatti on-chain)</h2>
      <div className="note">Ogni riga è un fatto osservato sulla blockchain, con l'età del token in quel momento. Non è un consiglio.</div>
      <table><thead><tr><th>Età</th><th>Evento</th><th>Dettaglio</th><th className="num">Prezzo (SOL)</th></tr></thead>
        <tbody>{events.map((e: any, i: number) => (
          <tr key={i}><td className="num">{age(e.age_s)}</td><td>{JOURNAL_LABEL[e.kind] ?? e.kind}</td><td>{journalValue(e)}</td>
            <td className="num mono">{e.price != null ? e.price.toExponential(3) : ""}</td></tr>
        ))}</tbody></table>
    </div>
  );
}
