import { useCallback, useEffect, useRef, useState } from "react";

const KEY = "mci_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(t: string | null) {
  try {
    if (t) localStorage.setItem(KEY, t);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: session-only login */
  }
  memToken = t;
}

let memToken: string | null = getToken();

export class AuthError extends Error {}

/** Static, read-only build (GitHub Pages): data comes from JSON files exported by the bot. */
export const STATIC = import.meta.env.VITE_STATIC === "1";
export const READ_ONLY_MSG = "Dashboard pubblica in sola lettura: usa i comandi Telegram (/pause, /resume, /kill).";

const SORT_KEYS: Record<string, string> = {
  score: "score", volume: "volume_h24", liquidity: "liquidity_usd", mcap: "mcap_usd", momentum: "change_h1",
  growth: "change_h1", recent: "first_seen_at", risk: "risk",
};

function staticTarget(path: string): { file: string; transform?: (d: any) => any } {
  const [p, qs] = path.split("?");
  const q = new URLSearchParams(qs || "");
  if (p.startsWith("/tokens/")) return { file: `tokens/${p.slice(8)}.json` };
  if (p === "/scanner")
    return {
      file: "scanner.json",
      transform: (d) => {
        let rows: any[] = d.tokens ?? [];
        if (q.get("include_excluded") !== "true") rows = rows.filter((t) => t.status !== "excluded");
        const s = (q.get("q") || "").toLowerCase();
        if (s) rows = rows.filter((t) => (t.symbol || "").toLowerCase().includes(s) || t.address === q.get("q"));
        const key = SORT_KEYS[q.get("sort") || "score"] || "score";
        rows = [...rows].sort((a, b) => ((b[key] ?? -Infinity) > (a[key] ?? -Infinity) ? 1 : -1));
        return { tokens: rows };
      },
    };
  if (p === "/positions")
    return {
      file: "positions.json",
      transform: (d) => {
        const st = q.get("status");
        return st && st !== "all" ? { positions: d.positions.filter((x: any) => x.status === st) } : d;
      },
    };
  if (p === "/logs")
    return {
      file: "logs.json",
      transform: (d) => {
        const c = q.get("category");
        return c ? { events: d.events.filter((e: any) => e.category === c) } : d;
      },
    };
  return { file: p.slice(1).replace(/\//g, "_") + ".json" };
}

async function staticApi<T>(path: string, init: RequestInit): Promise<T> {
  if (init.method && init.method !== "GET") throw new Error(READ_ONLY_MSG);
  if (path.startsWith("/backtests/")) throw new Error("dettaglio backtest non disponibile nella dashboard statica");
  const { file, transform } = staticTarget(path);
  const r = await fetch(`./data/${file}`, { cache: "no-store" });
  if (!r.ok) throw new Error(r.status === 404 ? "dato non ancora pubblicato dal bot" : `HTTP ${r.status}`);
  const d = await r.json();
  return (transform ? transform(d) : d) as T;
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  if (STATIC) return staticApi<T>(path, init);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const tok = memToken ?? getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const r = await fetch(`/api${path}`, { ...init, headers: { ...headers, ...(init.headers as any) } });
  if (r.status === 401) {
    setToken(null);
    window.dispatchEvent(new Event("mci-logout"));
    throw new AuthError("sessione scaduta");
  }
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      msg = (await r.json()).detail ?? msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json();
}

export async function login(username: string, password: string) {
  const r = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    let msg = "accesso non riuscito";
    try {
      msg = (await r.json()).detail ?? msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  const d = await r.json();
  setToken(d.token);
}

/** Fetch + auto refresh. */
export function usePoll<T>(path: string | null, intervalMs = 30000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);
  const load = useCallback(async () => {
    if (!path) return;
    try {
      const d = await api<T>(path);
      if (alive.current) {
        setData(d);
        setError(null);
      }
    } catch (e: any) {
      if (alive.current) setError(e.message);
    } finally {
      if (alive.current) setLoading(false);
    }
  }, [path]);
  useEffect(() => {
    alive.current = true;
    setLoading(true);
    load();
    const id = intervalMs > 0 ? window.setInterval(load, intervalMs) : undefined;
    return () => {
      alive.current = false;
      if (id) window.clearInterval(id);
    };
  }, [load, intervalMs]);
  return { data, error, loading, reload: load };
}
