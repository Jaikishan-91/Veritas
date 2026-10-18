import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import "./index.css";
import UploadPage from "./pages/UploadPage";
import DocumentPage from "./pages/DocumentPage";
import ReviewQueuePage from "./pages/ReviewQueuePage";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-200"}`;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center gap-6">
          <span className="font-semibold tracking-tight">Veritas</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>Analyze</NavLink>
            <NavLink to="/reviews" className={link}>Review queue</NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/reviews" element={<ReviewQueuePage />} />
        </Routes>
      </main>
    </BrowserRouter>
  </StrictMode>,
);
