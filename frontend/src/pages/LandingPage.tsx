import { Link } from "react-router-dom";

const FEATURES = [
  { title: "Risk score, not a verdict", body: "Each document gets a 0–1 integrity risk score with a band, so you can prioritise instead of trusting a yes/no label." },
  { title: "See where, not just whether", body: "Suspicious regions are boxed on the page. Error-level and noise heatmaps show inconsistencies you can inspect yourself." },
  { title: "Evidence you can explain", body: "Every point of the score traces back to a finding: hidden text, font mismatches, cloned regions, metadata edits." },
  { title: "Human review built in", body: "Uncertain cases are routed to reviewers automatically. Their decisions are recorded alongside the evidence." },
];

const CHECKS = ["Text tampering & white-box overwrites", "Copy-move cloning", "Splicing (ELA & noise)", "Font & layout mismatches",
  "Metadata & incremental-edit history"];

export default function LandingPage() {
  return (
    <div>
      <section className="bg-white border-b">
        <div className="mx-auto max-w-5xl px-4 py-20 text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-blue-700">Document integrity analysis</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Find out if a document was altered, and where.</h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
            Upload a PDF, PNG or JPG. Veritas combines file-structure, metadata and visual forensics into a risk score with
            highlighted regions and evidence.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Link to="/signup" className="rounded-lg bg-slate-900 px-5 py-2.5 text-white">Get started</Link>
            <Link to="/login" className="rounded-lg border px-5 py-2.5 hover:bg-slate-50">Sign in</Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-16 grid gap-6 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-xl border bg-white p-6">
            <h2 className="font-semibold">{f.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{f.body}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-20 grid gap-10 sm:grid-cols-2">
        <div>
          <h2 className="text-xl font-semibold">How it works</h2>
          <ol className="mt-4 space-y-3 text-sm text-slate-700">
            {["Create an account and verify your email.", "Upload a document. Analysis takes a few seconds.",
              "Review the score, highlighted regions and evidence list.", "Flagged cases go to a reviewer for a decision."]
              .map((s, i) => (
                <li key={s} className="flex gap-3"><span className="grid size-6 shrink-0 place-items-center rounded-full bg-slate-900 text-xs text-white">{i + 1}</span>{s}</li>
              ))}
          </ol>
        </div>
        <div>
          <h2 className="text-xl font-semibold">What it checks</h2>
          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            {CHECKS.map((c) => <li key={c} className="flex gap-2"><span className="text-emerald-600">✓</span>{c}</li>)}
          </ul>
          <p className="mt-4 text-xs text-slate-500">Your documents are private: only you can see them, unless one is flagged for human review.</p>
        </div>
      </section>
    </div>
  );
}
