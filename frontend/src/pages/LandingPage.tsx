import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "../theme";

const FEATURES = [
  { title: "Risk score, not a verdict", body: "Each document gets a 0–1 integrity risk score with a band, so you can prioritise instead of trusting a yes/no label." },
  { title: "See where, not just whether", body: "Suspicious regions are boxed on the page. Error-level and noise heatmaps show inconsistencies you can inspect yourself." },
  { title: "Evidence you can explain", body: "Every point of the score traces back to a finding: hidden text, font mismatches, cloned regions, metadata edits." },
  { title: "Human review built in", body: "Uncertain cases are routed to organisations for review automatically. Their decisions are recorded alongside the evidence." },
];

const CHECKS = ["Text tampering & white-box overwrites", "Copy-move cloning", "Splicing (ELA & noise)", "Font & layout mismatches",
  "Metadata & incremental-edit history"];

export default function LandingPage() {
  const { user } = useAuth();
  return (
    <div>
      <section className="relative overflow-hidden border-b border-line">
        <div aria-hidden className="pointer-events-none absolute inset-0"
          style={{ background: "radial-gradient(60% 70% at 50% 0%, color-mix(in srgb, var(--color-brand) 18%, transparent), transparent 70%)" }} />
        <div className="relative mx-auto max-w-5xl px-4 py-24 text-center">
          <div className="flex justify-center"><Logo size={56} /></div>
          <p className="mt-8 text-sm font-medium uppercase tracking-wider text-brand">Document integrity analysis</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-fg sm:text-6xl">Find out if a document was altered, and where.</h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted">
            Upload a PDF, PNG or JPG. Veritas combines file-structure, metadata and visual forensics into a risk score with
            highlighted regions and evidence.
          </p>
          <div className="mt-10 flex justify-center gap-3">
            {user ? <Link to="/dashboard" className="btn btn-primary px-6 py-2.5">Go to dashboard</Link> : <>
              <Link to="/signup" className="btn btn-primary px-6 py-2.5">Get started</Link>
              <Link to="/login" className="btn btn-ghost px-6 py-2.5 border border-line">Sign in</Link>
            </>}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 grid gap-6 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <div key={f.title} className="card p-6">
            <h2 className="font-semibold text-fg">{f.title}</h2>
            <p className="mt-2 text-sm text-muted">{f.body}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-20 grid gap-10 sm:grid-cols-2">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-fg">How it works</h2>
          <ol className="mt-4 space-y-3 text-sm text-muted">
            {["Create an account and verify your email.", "Upload a document. Analysis takes a few seconds.",
              "Review the score, highlighted regions and evidence list.", "Flagged cases go to an organisation for a decision."]
              .map((s, i) => (
                <li key={s} className="flex gap-3"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand text-xs text-brand-fg">{i + 1}</span>{s}</li>
              ))}
          </ol>
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-fg">What it checks</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted">
            {CHECKS.map((c) => (
              <li key={c} className="flex items-center gap-2.5">
                <span className="grid size-5 shrink-0 place-items-center rounded-full bg-brand-soft text-brand">
                  <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
                </span>{c}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-muted">Your documents are private: only you can see them, unless one is flagged for human review.</p>
        </div>
      </section>
    </div>
  );
}
