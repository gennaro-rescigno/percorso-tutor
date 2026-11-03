import { usePoll } from "../api";
import { MultiLine } from "../components/charts";
import { DataTable, ErrorBox, Kpi, Status } from "../components/ui";
import { fmtNum } from "../format";

const pct = (v: number | null | undefined) => v == null || Number.isNaN(v) ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

export default function Trend() {
  const { data, error } = usePoll<any>("/trend", 120000);
  const book = data?.book;
  const sm = data?.summary ?? {};
  const bt = data?.backtest;
  const hist = (book?.history ?? []).map((h: any) => ({ day: h.day, filtro: h.equity, comprato: h.bh }));
  const years = Object.entries(bt?.anni ?? {}) as [string, number[]][];
  return (
    <>
      <h1 style={{ fontSize: 20, marginTop: 0 }}>Trend BTC · ETH · SOL (portafoglio virtuale)</h1>
      <ErrorBox error={error} />
      <div className="note">{data?.note}</div>
      <div className="grid kpis section">
        <Kpi label="Valore attuale" value={sm.equity_usd != null ? `${fmtNum(sm.equity_usd)} $` : "–"} sub={`partenza ${fmtNum(book?.start_usd)} $ · dal ${book?.started ?? "–"}`} />
        <Kpi label="Rendimento" value={pct(sm.return_pct)} sub={`compra e tieni: ${pct(sm.bh_return_pct)}`} />
        <Kpi label="Perdita massima" value={pct(sm.max_drawdown_pct)} />
        <Kpi label="Operazioni" value={fmtNum(sm.trades ?? 0)} sub={`costi ${fmtNum(sm.costs_usd ?? 0)} $`} />
      </div>
      <div className="card section">
        <h2>Segnali di oggi (chiusura del {book?.last_day ?? "–"})</h2>
        <table><tbody>
          {Object.entries(book?.signals ?? {}).map(([a, s]: any) => (
            <tr key={a}><td><b>{a}</b></td>
              <td><Status level={s ? "good" : "warning"} label={s == null ? "storico insufficiente" : s ? "sopra la media di 50 giorni: investito" : "sotto la media di 50 giorni: in liquidità"} /></td>
              <td className="num">{book?.units?.[a] ? `${book.units[a].toPrecision(4)} ${a}` : "0"}</td></tr>
          ))}
        </tbody></table>
        {!book && <div className="muted">Il portafoglio parte alla prima chiusura giornaliera (00:00 UTC) dopo l'avvio.</div>}
      </div>
      <div className="card section">
        <h2>Valore: strategia contro compra e tieni (USD)</h2>
        <MultiLine data={hist} x="day" series={[{ key: "filtro", name: "Filtro di trend" }, { key: "comprato", name: "Compra e tieni" }]} fmt={(v) => `${v.toFixed(0)} $`} />
      </div>
      {bt && (
        <div className="card section">
          <h2>Perché questa strategia: la verifica storica</h2>
          <div className="note">Dati Binance 2018-2026 di tutte le coppie (anche quelle fallite). La media di 50 giorni è stata scelta solo sul 2018-2021;
            i numeri sotto sono del periodo successivo, {bt.periodo_fuori_campione}, mai usato per scegliere. Il filtro vince su {bt.monete_dove_il_filtro_vince}.
            L'intervallo di confidenza dello Sharpe ({bt.portafoglio_filtro.sharpe_ic95[0]} / {bt.portafoglio_filtro.sharpe_ic95[1]}) tocca ancora lo zero: è un'indicazione forte, non una garanzia.</div>
          <table><thead><tr><th></th><th className="num">Rendimento annuo</th><th className="num">Perdita massima</th></tr></thead><tbody>
            <tr><td>Con il filtro di trend</td><td className="num">{pct(bt.portafoglio_filtro.cagr_pct)}</td><td className="num">{pct(bt.portafoglio_filtro.max_drawdown_pct)}</td></tr>
            <tr><td>Con il filtro, eseguito un giorno dopo</td><td className="num">{pct(bt.con_un_giorno_di_ritardo.cagr_pct)}</td><td className="num">{pct(bt.con_un_giorno_di_ritardo.max_drawdown_pct)}</td></tr>
            <tr><td>Compra e tieni</td><td className="num">{pct(bt.compra_e_tieni.cagr_pct)}</td><td className="num">{pct(bt.compra_e_tieni.max_drawdown_pct)}</td></tr>
          </tbody></table>
          <table style={{ marginTop: 8 }}><thead><tr><th>Anno</th><th className="num">Filtro</th><th className="num">Compra e tieni</th></tr></thead><tbody>
            {years.map(([y, v]) => <tr key={y}><td>{y}</td><td className="num">{pct(v[0])}</td><td className="num">{pct(v[1])}</td></tr>)}
          </tbody></table>
        </div>
      )}
      <div className="card section">
        <h2>Operazioni virtuali</h2>
        <DataTable rows={[...(book?.trades ?? [])].reverse()} empty="Nessuna operazione ancora" columns={[
          { key: "day", label: "Giorno" }, { key: "asset", label: "Moneta" }, { key: "side", label: "Lato" },
          { key: "usd", label: "Importo $", num: true }, { key: "price", label: "Prezzo $", num: true },
          { key: "cost_usd", label: "Costo $", num: true }, { key: "reason", label: "Motivo" },
        ]} />
      </div>
    </>
  );
}
