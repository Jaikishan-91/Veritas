import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AuthCard, Field } from "../components/AuthCard";

const RESEND_SECONDS = 60;

export default function SignupPage() {
  const [params] = useSearchParams();
  const pending = params.get("verify");
  const [email, setEmail] = useState(pending ?? "");
  const [step, setStep] = useState<"form" | "verify">(pending ? "verify" : "form");

  return step === "form"
    ? <SignupForm email={email} setEmail={setEmail} onSent={() => setStep("verify")} />
    : <VerifyForm email={email} onBack={() => setStep("form")} />;
}

function SignupForm({ email, setEmail, onSent }: { email: string; setEmail: (v: string) => void; onSent: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) return setError("Passwords do not match");
    setBusy(true);
    setError(null);
    try {
      await api.signup(email, password);
      onSent();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Create your account" subtitle="We'll email you a 6-digit code to verify your address"
              footer={<>Already registered? <Link to="/login" className="text-blue-700 hover:underline">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password (min 10 characters)" type="password" required minLength={10} autoComplete="new-password"
               value={password} onChange={(e) => setPassword(e.target.value)} />
        <Field label="Confirm password" type="password" required minLength={10} autoComplete="new-password"
               value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        {error && <p className="rounded bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
        <button disabled={busy} className="w-full rounded bg-slate-900 py-2 text-white disabled:opacity-50">
          {busy ? "Sending code…" : "Sign up"}
        </button>
      </form>
    </AuthCard>
  );
}

function VerifyForm({ email, onBack }: { email: string; onBack: () => void }) {
  const { verify } = useAuth();
  const nav = useNavigate();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(RESEND_SECONDS);

  useEffect(() => {
    if (wait <= 0) return;
    const t = window.setTimeout(() => setWait(wait - 1), 1000);
    return () => window.clearTimeout(t);
  }, [wait]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await verify(email, code);
      nav("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    await api.resend(email).catch((e) => setError(e.message));
    setInfo("If the account is pending verification, a new code is on its way.");
    setWait(RESEND_SECONDS);
  }

  return (
    <AuthCard title="Check your email" subtitle={`Enter the 6-digit code sent to ${email}`}
              footer={<button onClick={onBack} className="text-blue-700 hover:underline">Use a different email</button>}>
      <form onSubmit={submit} className="space-y-4">
        <input inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} required autoFocus
               value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
               className="w-full rounded border px-3 py-2 text-center text-2xl tracking-[0.5em] tabular-nums" placeholder="••••••" />
        {error && <p className="rounded bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
        {info && <p className="rounded bg-slate-50 p-2 text-xs text-slate-600">{info}</p>}
        <button disabled={busy || code.length !== 6} className="w-full rounded bg-slate-900 py-2 text-white disabled:opacity-50">
          {busy ? "Verifying…" : "Verify and continue"}
        </button>
        <button type="button" onClick={resend} disabled={wait > 0}
                className="w-full text-sm text-blue-700 hover:underline disabled:text-slate-400 disabled:no-underline">
          {wait > 0 ? `Resend code in ${wait}s` : "Resend code"}
        </button>
      </form>
    </AuthCard>
  );
}
