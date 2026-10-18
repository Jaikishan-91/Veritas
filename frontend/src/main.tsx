import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import "./index.css";
import { AuthProvider, useAuth } from "./auth";
import { PublicHeader } from "./components/AuthCard";
import HomePage from "./pages/HomePage";
import LandingPage from "./pages/LandingPage";
import UploadPage from "./pages/UploadPage";
import DocumentPage from "./pages/DocumentPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import UsersPage from "./pages/UsersPage";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`;

function PublicApp() {
  return (
    <>
      <PublicHeader />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
}

function App() {
  const { user, loading, logout } = useAuth();
  if (loading) return <p className="p-6 text-slate-500">Loading…</p>;
  if (!user) return <PublicApp />;
  const reviewer = user.role === "reviewer" || user.role === "admin";
  const admin = user.role === "admin";
  return (
    <>
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
          <span className="font-semibold tracking-tight">Veritas</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>Home</NavLink>
            <NavLink to="/analyze" className={link}>Analyze</NavLink>
            {reviewer && <NavLink to="/reviews" className={link}>Review queue</NavLink>}
            {admin && <NavLink to="/users" className={link}>Users</NavLink>}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-600">
            <span className="hidden sm:inline">{user.email} · {user.role}</span>
            <button onClick={logout} className="rounded border px-2 py-1 hover:bg-slate-100">Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/analyze" element={<UploadPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/reviews" element={reviewer ? <ReviewQueuePage /> : <Navigate to="/" />} />
          <Route path="/users" element={admin ? <UsersPage /> : <Navigate to="/" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
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
