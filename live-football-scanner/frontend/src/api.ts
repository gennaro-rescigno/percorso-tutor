import { useEffect, useRef, useState } from "react";
import type { LiveState } from "./types";

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = `${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail ?? msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return (await r.json()) as T;
}

export async function postJSON<T>(path: string): Promise<T> {
  const r = await fetch(path, { method: "POST" });
  if (!r.ok) throw new Error(`${r.status}`);
  return (await r.json()) as T;
}

/** Live state via WebSocket, with REST polling fallback (every 30 s) if the socket drops. */
export function useLiveState() {
  const [state, setState] = useState<LiveState | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let closed = false;
    let retry: number | undefined;
    let poll: number | undefined;

    const fetchOnce = () =>
      getJSON<LiveState>("/api/state")
        .then((s) => {
          setState(s);
          setError(null);
        })
        .catch((e) => setError(String(e)));

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws`);
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };
      ws.onmessage = (ev) => {
        try {
          setState(JSON.parse(ev.data));
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = window.setTimeout(connect, 5000);
      };
      ws.onerror = () => ws.close();
    };

    fetchOnce();
    connect();
    poll = window.setInterval(() => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) fetchOnce();
    }, 30000);
    return () => {
      closed = true;
      window.clearTimeout(retry);
      window.clearInterval(poll);
      wsRef.current?.close();
    };
  }, []);

  return { state, setState, connected, error };
}

export const pct = (x: number | null | undefined, d = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : `${(100 * x).toFixed(d)}%`;
export const signedPct = (x: number | null | undefined, d = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : `${x >= 0 ? "+" : ""}${(100 * x).toFixed(d)}%`;
export const num = (x: number | null | undefined, d = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(d);

export function minuteLabel(status: string, elapsed: number | null, extra: number | null) {
  if (status === "HT") return "Intervallo";
  if (elapsed === null) return status;
  return extra ? `${elapsed}+${extra}'` : `${elapsed}'`;
}

export function ago(iso: string | null | undefined, now: number) {
  if (!iso) return "mai";
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s fa`;
  if (s < 3600) return `${Math.floor(s / 60)} min fa`;
  return `${Math.floor(s / 3600)} h fa`;
}
