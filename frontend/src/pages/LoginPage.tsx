import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AuthCard, Field } from "../components/AuthCard";

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
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
      nav("/");
    } catch (err) {
      const msg = (err as Error).message;
      if (msg === "email_not_verified") {
        await api.resend(email).catch(() => {});
        nav(`/signup?verify=${encodeURIComponent(email)}`);
        return;
      }
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Sign in" subtitle="Welcome back to Veritas"
              footer={<>No account? <Link to="/signup" className="text-blue-700 hover:underline">Create one</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" required autoComplete="current-password" value={password}
               onChange={(e) => setPassword(e.target.value)} />
        {error && <p className="rounded bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
        <button disabled={busy} className="w-full rounded bg-slate-900 py-2 text-white disabled:opacity-50">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthCard>
  );
}
