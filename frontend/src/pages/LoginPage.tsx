import { useState } from "react";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border bg-white p-6 shadow-sm">
        <div>
          <h1 className="text-xl font-semibold">Veritas</h1>
          <p className="text-sm text-slate-500">Sign in to analyse documents</p>
        </div>
        <label className="block text-sm">
          Email
          <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
                 className="mt-1 w-full rounded border px-2 py-1.5" />
        </label>
        <label className="block text-sm">
          Password
          <input type="password" required autoComplete="current-password" value={password}
                 onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5" />
        </label>
        {error && <p className="rounded bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
        <button disabled={busy} className="w-full rounded bg-slate-900 py-2 text-white disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
