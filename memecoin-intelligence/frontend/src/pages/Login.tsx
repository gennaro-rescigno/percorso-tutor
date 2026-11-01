import { FormEvent, useState } from "react";
import { login } from "../api";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [u, setU] = useState("admin");
  const [p, setP] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await login(u, p);
      onLogin();
    } catch (x: any) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h2 style={{ color: "var(--text-primary)", fontSize: 18 }}>Memecoin Intelligence</h2>
        <label className="muted">Utente<input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" style={{ width: "100%" }} /></label>
        <label className="muted">Password<input type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" style={{ width: "100%" }} /></label>
        {err && <div className="warn-box">{err}</div>}
        <button className="primary" disabled={busy || !p}>{busy ? "Accesso…" : "Accedi"}</button>
      </form>
    </div>
  );
}
