import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import "./index.css";
import { AuthProvider, useAuth } from "./auth";
import UploadPage from "./pages/UploadPage";
import DocumentPage from "./pages/DocumentPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import LoginPage from "./pages/LoginPage";
import UsersPage from "./pages/UsersPage";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`;

function App() {
  const { user, loading, logout } = useAuth();
  if (loading) return <p className="p-6 text-slate-500">Loading…</p>;
  if (!user) return <LoginPage />;
  const reviewer = user.role === "reviewer" || user.role === "admin";
  const admin = user.role === "admin";
  return (
    <>
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
          <span className="font-semibold tracking-tight">Veritas</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>Analyze</NavLink>
            {reviewer && <NavLink to="/reviews" className={link}>Review queue</NavLink>}
            {admin && <NavLink to="/users" className={link}>Users</NavLink>}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-600">
            <span>{user.email} · {user.role}</span>
            <button onClick={logout} className="rounded border px-2 py-1 hover:bg-slate-100">Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/reviews" element={reviewer ? <ReviewQueuePage /> : <Navigate to="/" />} />
          <Route path="/users" element={admin ? <UsersPage /> : <Navigate to="/" />} />
        </Routes>
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
