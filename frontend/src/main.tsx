import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import "./index.css";
import { AuthProvider, useAuth } from "./auth";
import { PublicHeader } from "./components/AuthCard";
import { NotificationBell } from "./components/NotificationBell";
import HomePage from "./pages/HomePage";
import LandingPage from "./pages/LandingPage";
import UploadPage from "./pages/UploadPage";
import DocumentPage from "./pages/DocumentPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import UsersPage from "./pages/UsersPage";
import { Logo, ThemeToggle } from "./theme";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${isActive ? "bg-brand-soft text-brand" : "text-muted hover:text-fg hover:bg-surface-2"}`;

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
  const { user, loading } = useAuth();
  if (loading) return <p className="p-6 text-muted">Loading…</p>;
  if (!user) return <PublicApp />;
  return (
    <Routes>
      <Route path="/" element={<><PublicHeader /><LandingPage /></>} />
      <Route path="*" element={<SignedInApp />} />
    </Routes>
  );
}

function SignedInApp() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const reviewer = user.role === "admin" || (user.role === "organisation" && user.approved);
  const pendingOrg = user.role === "organisation" && !user.approved;
  const admin = user.role === "admin";
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-line bg-surface/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 h-16 flex items-center gap-6">
          <NavLink to="/"><Logo /></NavLink>
          <nav className="flex gap-1">
            <NavLink to="/dashboard" className={link}>Dashboard</NavLink>
            <NavLink to="/analyze" className={link}>Analyze</NavLink>
            {reviewer && <NavLink to="/reviews" className={link}>Review queue</NavLink>}
            {admin && <NavLink to="/users" className={link}>Users</NavLink>}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm text-muted">
            <NotificationBell />
            <ThemeToggle />
            <span className="hidden sm:inline px-2">{user.username ?? user.email} · <span className="capitalize">{user.role}</span></span>
            <button onClick={logout} className="btn-ghost px-3 py-1.5">Sign out</button>
          </div>
        </div>
      </header>
      {pendingOrg && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
          Your organisation is awaiting admin approval. You can't review documents until an admin approves it.
        </div>
      )}
      <main className="mx-auto max-w-7xl px-4 py-8">
        <Routes>
          <Route path="/dashboard" element={<HomePage />} />
          <Route path="/analyze" element={<UploadPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/reviews" element={reviewer ? <ReviewQueuePage /> : <Navigate to="/dashboard" />} />
          <Route path="/users" element={admin ? <UsersPage /> : <Navigate to="/dashboard" />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
