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
  const { user, loading, logout } = useAuth();
  if (loading) return <p className="p-6 text-muted">Loading…</p>;
  if (!user) return <PublicApp />;
  const reviewer = user.role === "reviewer" || user.role === "admin";
  const admin = user.role === "admin";
  return (
    <>
      <header className="sticky top-0 z-20 border-b border-line bg-surface/80 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 h-16 flex items-center gap-6">
          <NavLink to="/"><Logo /></NavLink>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>Home</NavLink>
            <NavLink to="/analyze" className={link}>Analyze</NavLink>
            {reviewer && <NavLink to="/reviews" className={link}>Review queue</NavLink>}
            {admin && <NavLink to="/users" className={link}>Users</NavLink>}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-sm text-muted">
            <NotificationBell />
            <ThemeToggle />
            <span className="hidden sm:inline px-2">{user.email} · <span className="capitalize">{user.role}</span></span>
            <button onClick={logout} className="btn-ghost px-3 py-1.5">Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8">
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
