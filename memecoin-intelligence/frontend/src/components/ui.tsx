import { ReactNode, useMemo, useState } from "react";

export function Kpi({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: string }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className={`value ${tone ?? ""}`}>{value}</div>
      {sub != null && <div className="sub">{sub}</div>}
    </div>
  );
}

export function ModeBadge({ mode }: { mode?: string }) {
  const live = mode === "live";
  return <span className={`badge ${live ? "live" : "paper"}`}>{live ? "💰 TRADING REALE" : "🧪 PAPER TRADING"}</span>;
}

/** Status always ships with an icon + label, never color alone. */
export function Status({ level, label }: { level: "good" | "warning" | "critical"; label: string }) {
  const icon = level === "good" ? "✓" : level === "warning" ? "!" : "✕";
  return (
    <span className="badge">
      <span className={`dot ${level}`} aria-hidden /> {icon} {label}
    </span>
  );
}

export function RiskBadge({ risk }: { risk?: string | null }) {
  if (!risk) return <span className="muted">n/d</span>;
  const level = risk === "basso" ? "good" : risk === "medio" ? "warning" : "critical";
  return <Status level={level} label={risk} />;
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="warn-box">⚠️ {error}</div>;
}

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
  value?: (row: T) => number | string | null | undefined;
  num?: boolean;
  sortable?: boolean;
}

export function DataTable<T>({
  rows, columns, onRowClick, initialSort, empty = "Nessun dato",
}: {
  rows: T[]; columns: Column<T>[]; onRowClick?: (r: T) => void; initialSort?: { key: string; desc: boolean };
  empty?: string;
}) {
  const [sort, setSort] = useState(initialSort ?? { key: "", desc: true });
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const get = col.value ?? ((r: any) => r[col.key]);
    return [...rows].sort((a, b) => {
      const va = get(a), vb = get(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const c = va < vb ? -1 : va > vb ? 1 : 0;
      return sort.desc ? -c : c;
    });
  }, [rows, columns, sort]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`${c.num ? "num" : ""} ${c.sortable !== false ? "sortable" : ""} ${sort.key === c.key ? "sorted" : ""}`}
                onClick={() => c.sortable !== false && setSort({ key: c.key, desc: sort.key === c.key ? !sort.desc : true })}
              >
                {c.label}
                {sort.key === c.key ? (sort.desc ? " ↓" : " ↑") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="muted">{empty}</td>
            </tr>
          )}
          {sorted.map((r, i) => (
            <tr key={i} className={onRowClick ? "clickable" : ""} onClick={() => onRowClick?.(r)}>
              {columns.map((c) => (
                <td key={c.key} className={c.num ? "num" : ""}>
                  {c.render ? c.render(r) : String((r as any)[c.key] ?? "n/d")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ScoreBars({ categories }: { categories: Record<string, any> }) {
  return (
    <div>
      {Object.entries(categories).map(([k, c]) => (
        <div className="bar-row" key={k} title={`copertura dati ${Math.round(c.coverage * 100)}%`}>
          <span>{c.label}</span>
          <div className="bar-track" role="img" aria-label={`${c.label} ${c.points} su ${c.max}`}>
            <div className="bar-fill" style={{ width: `${(100 * c.points) / c.max}%` }} />
          </div>
          <span className="num">{c.points}/{c.max}</span>
        </div>
      ))}
    </div>
  );
}
