/**
 * Login page — route `/login`.
 * Calls `/api/auth/login`, stores the token, then enters `/app`.
 */
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "@/api/auth";
import { setSession } from "@/lib/auth";

type Phase = "idle" | "loading" | "error";

export default function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setPhase("loading");
    setError(null);
    try {
      const result = await authApi.login(username.trim(), password);
      setSession({
        token: result.token,
        username: result.username,
        role: result.role,
        displayName: result.display_name,
      });
      const from = params.get("from");
      navigate(from && from.startsWith("/") && !from.startsWith("/login") ? from : "/app", {
        replace: true,
      });
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-12 lg:grid lg:grid-cols-2 lg:items-center lg:gap-16">
      <div className="mb-10 lg:mb-0">
        <Link to="/" className="text-sm text-[var(--ink-muted)] hover:text-[var(--ink)]">
          ← Back to ShelfMate
        </Link>
        <h1
          className="mt-6 text-4xl tracking-tight sm:text-5xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Sign in to the floor assistant
        </h1>
        <p className="mt-4 max-w-md text-[var(--ink-muted)]">
          Demo accounts stay local. Use them to ask policy questions, look up
          mock orders, and escalate gaps to Ops.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="rounded-[1.75rem] border border-[var(--line)] bg-[var(--bg-elevated)]/80 p-8 shadow-[0_30px_60px_rgba(0,0,0,0.25)] backdrop-blur"
      >
        <label className="block text-sm text-[var(--ink-muted)]">
          Username
          <input
            className="mt-2 w-full rounded-xl border border-[var(--line)] bg-black/20 px-4 py-3 outline-none ring-[var(--accent)] focus:ring-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="mt-4 block text-sm text-[var(--ink-muted)]">
          Password
          <input
            type="password"
            className="mt-2 w-full rounded-xl border border-[var(--line)] bg-black/20 px-4 py-3 outline-none ring-[var(--accent)] focus:ring-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {error ? (
          <p className="mt-4 text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={phase === "loading"}
          className="btn-accent mt-6 w-full rounded-full px-4 py-3 text-sm font-semibold transition hover:brightness-110 disabled:opacity-60"
          style={{ color: "#102016" }}
        >
          {phase === "loading" ? "Signing in…" : "Sign in"}
        </button>

        <p className="mt-4 text-xs text-[var(--ink-muted)]">
          Try <code>admin / admin123</code> or <code>store / store123</code>.
        </p>
      </form>
    </div>
  );
}
