import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AuthCard({ title, subtitle, children, footer }: {
  title: string; subtitle: string; children: ReactNode; footer: ReactNode;
}) {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] grid place-items-center px-4 py-10">
      <div className="w-full max-w-sm space-y-4">
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <div>
            <h1 className="text-xl font-semibold">{title}</h1>
            <p className="text-sm text-slate-500">{subtitle}</p>
          </div>
          {children}
        </div>
        <p className="text-center text-sm text-slate-600">{footer}</p>
      </div>
    </div>
  );
}

export function Field(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block text-sm">
      {label}
      <input {...rest} className="mt-1 w-full rounded border px-2 py-1.5" />
    </label>
  );
}

export function PublicHeader() {
  return (
    <header className="border-b bg-white">
      <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
        <Link to="/" className="font-semibold tracking-tight">Veritas</Link>
        <div className="ml-auto flex gap-2 text-sm">
          <Link to="/login" className="rounded px-3 py-1.5 hover:bg-slate-100">Sign in</Link>
          <Link to="/signup" className="rounded bg-slate-900 px-3 py-1.5 text-white">Sign up</Link>
        </div>
      </div>
    </header>
  );
}
