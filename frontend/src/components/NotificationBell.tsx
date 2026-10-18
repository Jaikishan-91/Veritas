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
              className="relative rounded border px-2 py-1 hover:bg-slate-100">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1.5 -top-1.5 grid min-w-4 h-4 place-items-center rounded-full bg-rose-600 px-1 text-[10px] font-semibold text-white">
            {unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border bg-white shadow-lg">
          <div className="flex items-center justify-between border-b px-3 py-2 text-sm">
            <span className="font-semibold">Notifications</span>
            {unread > 0 && (
              <button className="text-xs text-blue-700 hover:underline" onClick={() => api.markAllRead().then(load)}>Mark all read</button>
            )}
          </div>
          <ul className="max-h-96 overflow-auto text-sm">
            {items.length === 0 && <li className="px-3 py-4 text-slate-500">No notifications yet.</li>}
            {items.map((n) => (
              <li key={n.id}>
                <button onClick={() => openItem(n)} className={`w-full px-3 py-2 text-left hover:bg-slate-50 ${n.read ? "text-slate-500" : ""}`}>
                  <div className="flex gap-2">
                    {!n.read && <span className="mt-1.5 size-2 shrink-0 rounded-full bg-blue-600" />}
                    <span>{n.message}</span>
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
