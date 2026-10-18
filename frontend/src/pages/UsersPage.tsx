import { useEffect, useState } from "react";
import { api, type Role, type User } from "../api";
import { useAuth } from "../auth";

const ROLES: Role[] = ["analyst", "reviewer", "admin"];

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", password: "", role: "analyst" as Role });

  const load = () => api.users().then(setUsers).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function run(p: Promise<unknown>) {
    setError(null);
    try { await p; await load(); } catch (e) { setError((e as Error).message); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await run(api.createUser(form));
    setForm({ email: "", password: "", role: "analyst" });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Users</h1>
      {error && <p className="rounded bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      <form onSubmit={create} className="flex flex-wrap items-end gap-2 rounded-lg border bg-white p-4 text-sm">
        <label>Email<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                           className="mt-1 block rounded border px-2 py-1" /></label>
        <label>Password (min 10)<input type="password" required minLength={10} autoComplete="new-password" value={form.password}
                                       onChange={(e) => setForm({ ...form, password: e.target.value })}
                                       className="mt-1 block rounded border px-2 py-1" /></label>
        <label>Role<select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
                           className="mt-1 block rounded border px-2 py-1">{ROLES.map((r) => <option key={r}>{r}</option>)}</select></label>
        <button className="rounded bg-slate-900 px-3 py-1.5 text-white">Add user</button>
      </form>
      <table className="w-full text-sm bg-white border rounded-lg overflow-hidden">
        <thead className="bg-slate-100 text-left text-slate-600">
          <tr><th className="p-2">Email</th><th className="p-2">Role</th><th className="p-2">Status</th><th className="p-2" /></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-t">
              <td className="p-2">{u.email}</td>
              <td className="p-2">
                <select value={u.role} disabled={u.id === me?.id} className="rounded border px-1"
                        onChange={(e) => run(api.updateUser(u.id, { role: e.target.value as Role }))}>
                  {ROLES.map((r) => <option key={r}>{r}</option>)}
                </select>
              </td>
              <td className="p-2">{u.active ? "active" : <span className="text-slate-400">disabled</span>}</td>
              <td className="p-2 text-right">
                {u.id !== me?.id && (
                  <button className="text-blue-700 hover:underline" onClick={() => run(api.updateUser(u.id, { active: !u.active }))}>
                    {u.active ? "Disable" : "Enable"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
