import { useEffect, useState } from "react";
import { api, type Role, type User } from "../api";
import { useAuth } from "../auth";

const ROLES: Role[] = ["user", "organisation", "admin"];

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", username: "", password: "", role: "user" as Role });

  const load = () => api.users().then(setUsers).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function run(p: Promise<unknown>) {
    setError(null);
    try { await p; await load(); } catch (e) { setError((e as Error).message); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await run(api.createUser(form));
    setForm({ email: "", username: "", password: "", role: "user" });
  }

  const th = "px-4 py-3 font-medium";
  const lbl = "text-xs font-medium uppercase tracking-wide text-muted";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="mt-1 text-sm text-muted">Create accounts and manage roles and access.</p>
      </div>
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">{error}</p>}
      <form onSubmit={create} className="card flex flex-wrap items-end gap-3 p-4 text-sm">
        <label className={lbl}>Email<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                           className="input mt-1 block normal-case tracking-normal" /></label>
        <label className={lbl}>Username<input required pattern="[A-Za-z0-9._\-]{3,32}" title="3-32 letters, numbers, . _ -" value={form.username}
                           onChange={(e) => setForm({ ...form, username: e.target.value })}
                           className="input mt-1 block normal-case tracking-normal" /></label>
        <label className={lbl}>Password (min 10)<input type="password" required minLength={10} autoComplete="new-password" value={form.password}
                                       onChange={(e) => setForm({ ...form, password: e.target.value })}
                                       className="input mt-1 block normal-case tracking-normal" /></label>
        <label className={lbl}>Role<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
                           className="input mt-1 block normal-case tracking-normal">{ROLES.map((r) => <option key={r}>{r}</option>)}</select></label>
        <button className="btn btn-primary">Add user</button>
      </form>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs uppercase tracking-wide text-muted">
              <tr><th className={th}>Email</th><th className={th}>Username</th><th className={th}>Role</th><th className={th}>Status</th><th className={th} /></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-line hover:bg-surface-2">
                  <td className="px-4 py-3 font-medium text-fg">{u.email}</td>
                  <td className="px-4 py-3 text-muted">{u.username ?? "—"}</td>
                  <td className="px-4 py-3">
                    <select value={u.role} disabled={u.id === me?.id} className="input !w-auto !py-1"
                            onChange={(e) => run(api.updateUser(u.id, { role: e.target.value as Role }))}>
                      {ROLES.map((r) => <option key={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3">{u.active ? <span className="text-emerald-600 dark:text-emerald-400">active</span> : <span className="text-muted">disabled</span>}</td>
                  <td className="px-4 py-3 text-right space-x-3">
                    {u.role === "organisation" && (u.approved
                      ? <button className="text-sm font-medium text-muted hover:underline" onClick={() => run(api.updateUser(u.id, { approved: false }))}>Revoke approval</button>
                      : <>
                          <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">Pending</span>
                          <button className="btn btn-primary !py-1" onClick={() => run(api.updateUser(u.id, { approved: true }))}>Approve</button>
                        </>)}
                    {u.id !== me?.id && (
                      <button className="text-sm font-medium text-brand hover:underline" onClick={() => run(api.updateUser(u.id, { active: !u.active }))}>
                        {u.active ? "Disable" : "Enable"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
