/**
 * Settings shell — Chat model / Embedding / Vector store (KE-inspired, English).
 */
import { NavLink, Outlet } from "react-router-dom";
import { Bot, Boxes, Database } from "lucide-react";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/app/settings/chat-model", label: "Chat model", icon: Bot },
  { to: "/app/settings/embedding", label: "Embedding", icon: Boxes },
  { to: "/app/settings/vector-store", label: "Vector store", icon: Database },
] as const;

export default function SettingsLayout() {
  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
      <aside className="rounded-[1.5rem] border border-[var(--line)] bg-black/20 p-4">
        <h2 className="text-lg" style={{ fontFamily: "var(--font-display)" }}>
          Settings
        </h2>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">
          Switch LLM and embedding providers for customer demos.
        </p>
        <nav className="mt-4 space-y-1">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-sm",
                  isActive
                    ? "bg-[var(--accent)] text-[#102016]"
                    : "text-[var(--ink-muted)] hover:text-[var(--ink)]",
                )
              }
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="rounded-[1.5rem] border border-[var(--line)] bg-[var(--bg-elevated)]/70 p-6">
        <Outlet />
      </div>
    </div>
  );
}
