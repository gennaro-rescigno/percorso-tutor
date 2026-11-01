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

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
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
