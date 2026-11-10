/**
 * Authenticated workspace chrome — top nav for Chat / Knowledge / Settings.
 */
import { NavLink, Outlet, Link } from "react-router-dom";
import { BookOpen, LogOut, MessageSquare, Settings } from "lucide-react";
import { logout, useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";

const NAV = [
  { to: "/app", label: "Chat", icon: MessageSquare, end: true },
  { to: "/app/knowledge", label: "Knowledge", icon: BookOpen, end: false },
  { to: "/app/settings", label: "Settings", icon: Settings, end: false },
] as const;

export default function WorkspaceShell() {
  const { displayName, username } = useAuth();

  function onLogout() {
    logout();
    window.location.assign("/");
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] pb-4">
        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/"
            className="btn-accent grid h-9 w-9 place-items-center rounded-lg text-xs font-bold"
            style={{ color: "#102016" }}
          >
            SM
          </Link>
          <div>
            <div style={{ fontFamily: "var(--font-display)" }} className="text-lg">
              ShelfMate
            </div>
            <div className="text-xs text-[var(--ink-muted)]">
              {displayName || username}
            </div>
          </div>
          <nav className="ml-2 flex flex-wrap gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm",
                    isActive
                      ? "bg-[var(--accent)] text-[#102016]"
                      : "text-[var(--ink-muted)] hover:text-[var(--ink)]",
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-2 text-sm text-[var(--ink-muted)] hover:text-[var(--ink)]"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </header>
      <Outlet />
    </div>
  );
}
