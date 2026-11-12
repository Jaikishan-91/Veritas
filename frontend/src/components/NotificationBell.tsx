import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Notification } from "../api";

const POLL_MS = 30_000;

export function NotificationBell() {
  const nav = useNavigate();
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const load = useCallback(() => api.notifications().then(setItems).catch(() => {}), []);
  useEffect(() => {
    load();
    const t = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const unread = items.filter((n) => !n.read).length;

  async function openItem(n: Notification) {
    if (!n.read) await api.markRead(n.id).catch(() => {});
    setOpen(false);
    load();
    if (n.document_id) nav(`/documents/${n.document_id}`);
  }

  return (
    <div ref={ref} className="relative">
      <button onClick={() => { setOpen(!open); if (!open) load(); }} aria-label={`Notifications (${unread} unread)`}
              className="relative grid size-9 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-fg">
        <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute right-0.5 top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-brand px-1 text-[10px] font-semibold text-brand-fg ring-2 ring-surface">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <div className="card absolute right-0 z-20 mt-2 w-80 shadow-lg">
          <div className="flex items-center justify-between border-b border-line px-4 py-3 text-sm">
            <span className="font-semibold">Notifications</span>
            {unread > 0 && (
              <button className="text-xs font-medium text-brand hover:underline" onClick={() => api.markAllRead().then(load)}>Mark all read</button>
            )}
          </div>
          <ul className="max-h-96 divide-y divide-line overflow-auto text-sm">
            {items.length === 0 && <li className="px-4 py-6 text-center text-muted">No notifications yet.</li>}
            {items.map((n) => (
              <li key={n.id}>
                <button onClick={() => openItem(n)} className={`w-full px-4 py-3 text-left hover:bg-surface-2 ${n.read ? "text-muted" : "text-fg"}`}>
                  <div className="flex gap-2">
                    {!n.read && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-brand" />}
                    <span>{n.message}</span>
                  </div>
                  <div className="mt-0.5 text-xs text-muted">{new Date(n.created_at).toLocaleString()}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
