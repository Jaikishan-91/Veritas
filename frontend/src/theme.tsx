import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const KEY = "veritas-theme";

function initial(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initial);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);
  const next = theme === "dark" ? "light" : "dark";
  const flip = () => {
    setTheme(next);
    try { localStorage.setItem(KEY, next); } catch { /* storage blocked: theme still applies for this visit */ }
  };
  return (
    <button onClick={flip} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}
      className="grid size-9 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg transition-colors">
      {theme === "dark" ? (
        <svg viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      )}
    </button>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5 font-semibold tracking-tight text-fg">
      <img src="/logo.png" alt="" width={size} height={size}
        className="rounded-md object-cover ring-1 ring-line" style={{ width: size, height: size }} />
      Veritas
    </span>
  );
}
