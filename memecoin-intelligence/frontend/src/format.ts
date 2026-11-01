const it = (d: number) => new Intl.NumberFormat("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });

export const fmtSol = (x?: number | null, d = 4) => (x == null ? "n/d" : `${it(d).format(x)} SOL`);
export const fmtEur = (x?: number | null) => (x == null ? "n/d" : `${it(2).format(x)} €`);
export const fmtNum = (x?: number | null, d = 0) => (x == null ? "n/d" : it(d).format(x));
export const fmtPct = (x?: number | null, d = 1) =>
  x == null ? "n/d" : `${x >= 0 ? "+" : ""}${it(d).format(x * 100)}%`;
export const fmtPctPlain = (x?: number | null, d = 1) => (x == null ? "n/d" : `${it(d).format(x * 100)}%`);

export function fmtUsd(x?: number | null) {
  if (x == null) return "n/d";
  if (Math.abs(x) >= 1e6) return `${it(2).format(x / 1e6)} M$`;
  if (Math.abs(x) >= 1e3) return `${it(1).format(x / 1e3)} k$`;
  return `${it(0).format(x)} $`;
}

export function fmtPrice(x?: number | null) {
  if (x == null) return "n/d";
  if (x === 0) return "0";
  if (Math.abs(x) < 0.001) return x.toExponential(3).replace(".", ",");
  return it(6).format(x);
}

export function fmtTime(iso?: string | null) {
  if (!iso) return "n/d";
  const d = new Date(iso);
  return d.toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function fmtAge(hours?: number | null) {
  if (hours == null) return "n/d";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 48) return `${it(1).format(hours)} h`;
  return `${Math.round(hours / 24)} g`;
}

export const signClass = (x?: number | null) => (x == null ? "" : x > 0 ? "pos" : x < 0 ? "neg" : "");
