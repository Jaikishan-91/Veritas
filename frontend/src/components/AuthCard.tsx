import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo, ThemeToggle } from "../theme";

export function AuthCard({ title, subtitle, children, footer }: {
  title: string; subtitle: string; children: ReactNode; footer: ReactNode;
}) {
  return (
    <div className="min-h-[calc(100vh-4rem)] grid place-items-center px-4 py-10">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex justify-center"><Logo size={36} /></div>
        <div className="card p-6 space-y-5">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
            <p className="mt-1 text-sm text-muted">{subtitle}</p>
          </div>
          {children}
        </div>
        <p className="text-center text-sm text-muted">{footer}</p>
      </div>
    </div>
  );
}

export function Field(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block text-sm font-medium text-fg">
      {label}
      <input {...rest} className="input mt-1.5" />
    </label>
  );
}

export function PublicHeader() {
  const { user } = useAuth();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/80 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 h-16 flex items-center gap-6">
        <Link to="/"><Logo /></Link>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <ThemeToggle />
          {user ? <Link to="/dashboard" className="btn btn-primary">Go to dashboard</Link> : <>
            <Link to="/login" className="btn btn-ghost">Sign in</Link>
            <Link to="/signup" className="btn btn-primary">Sign up</Link>
          </>}
        </div>
      </div>
    </header>
  );
}
