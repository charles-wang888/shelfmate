/**
 * App shell — routing and login gate.
 *
 * Routes:
 *   /                      Product landing (public)
 *   /login                 Login
 *   /app                   Chat workspace
 *   /app/knowledge         Knowledge browser
 *   /app/settings/*        Model + vector settings
 */
import { useEffect, type ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";

import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import ChatPage from "@/pages/ChatPage";
import KnowledgePage from "@/pages/KnowledgePage";
import WorkspaceShell from "@/components/WorkspaceShell";
import SettingsLayout from "@/pages/settings/SettingsLayout";
import {
  ChatModelSettingsPage,
  EmbeddingSettingsPage,
} from "@/pages/settings/ModelSettingsPages";
import VectorStoreSettingsPage from "@/pages/settings/VectorStoreSettingsPage";
import { UNAUTHORIZED_EVENT, isLoggingOut, useAuth } from "@/lib/auth";

function safeFrom(pathname: string, search: string): string | null {
  if (pathname === "/login") return null;
  const full = pathname + search;
  return full.startsWith("/app") ? full : full;
}

function loginQuery(pathname: string, search: string): string {
  const from = safeFrom(pathname, search);
  const params = new URLSearchParams();
  if (from) params.set("from", from);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated && !isLoggingOut()) {
    return (
      <Navigate
        to={`/login${loginQuery(location.pathname, location.search)}`}
        replace
      />
    );
  }
  return <>{children}</>;
}

function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/app" replace />;
  return <>{children}</>;
}

function UnauthorizedWatcher() {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    const handler = () => {
      navigate(`/login${loginQuery(location.pathname, location.search)}`, {
        replace: true,
      });
    };
    window.addEventListener(UNAUTHORIZED_EVENT, handler);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handler);
  }, [navigate, location.pathname, location.search]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <UnauthorizedWatcher />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={
            <RedirectIfAuthed>
              <LoginPage />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/app"
          element={
            <RequireAuth>
              <WorkspaceShell />
            </RequireAuth>
          }
        >
          <Route index element={<ChatPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<Navigate to="chat-model" replace />} />
            <Route path="chat-model" element={<ChatModelSettingsPage />} />
            <Route path="embedding" element={<EmbeddingSettingsPage />} />
            <Route path="vector-store" element={<VectorStoreSettingsPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
