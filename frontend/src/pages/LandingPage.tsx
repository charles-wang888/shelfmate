/**
 * Product landing page — route `/`.
 * Brand-first retail ops composition for ShelfMate / NovaMart.
 */
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  LifeBuoy,
  PackageSearch,
  ShieldAlert,
} from "lucide-react";

const CAPABILITIES = [
  {
    icon: BookOpenCheck,
    title: "Grounded in store policy",
    desc: "Answers come from chunked policy docs in Weaviate — not model guesswork.",
  },
  {
    icon: PackageSearch,
    title: "Live order lookup",
    desc: "Ask for an order id and ShelfMate calls an MCP order tool for status and ETA.",
  },
  {
    icon: ShieldAlert,
    title: "Refuses when unsure",
    desc: "If the docs and tools cannot support an answer, it says so instead of inventing one.",
  },
  {
    icon: LifeBuoy,
    title: "Escalate to Ops",
    desc: "Close the loop: open a ticket with context when a human still needs to step in.",
  },
] as const;

export default function LandingPage() {
  return (
    <div className="min-h-screen text-[var(--ink)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <span
            className="btn-accent grid h-10 w-10 place-items-center rounded-xl text-sm font-bold"
            style={{ color: "#102016" }}
          >
            SM
          </span>
          <div>
            <div
              className="text-lg font-semibold tracking-tight"
              style={{ fontFamily: "var(--font-display)" }}
            >
              ShelfMate
            </div>
            <div className="text-xs text-[var(--ink-muted)]">for NovaMart</div>
          </div>
        </div>
        <Link
          to="/login"
          className="rounded-full border border-[var(--line)] px-4 py-2 text-sm text-[var(--ink-muted)] transition hover:border-[var(--accent)] hover:text-[var(--ink)]"
        >
          Sign in
        </Link>
      </header>

      <main>
        <section className="relative mx-auto grid max-w-6xl gap-10 px-6 pb-20 pt-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pt-16">
          <div>
            <p className="mb-4 text-sm uppercase tracking-[0.22em] text-[var(--warm)]">
              Internal store assistant
            </p>
            <h1
              className="max-w-xl text-5xl leading-[1.05] tracking-tight sm:text-6xl"
              style={{ fontFamily: "var(--font-display)" }}
            >
              ShelfMate
            </h1>
            <p className="mt-5 max-w-lg text-xl text-[var(--ink-muted)]">
              Policy answers, order status, and Ops escalation — right where
              associates already work the floor.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                to="/login"
                className="btn-accent inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition hover:brightness-110"
                style={{ color: "#102016" }}
              >
                Open workspace
                <ArrowRight className="h-4 w-4" style={{ color: "#102016" }} />
              </Link>
              <span className="text-sm text-[var(--ink-muted)]">
                Demo: admin / admin123
              </span>
            </div>
          </div>

          <div
            aria-hidden
            className="relative min-h-[340px] overflow-hidden rounded-[2rem] border border-[var(--line)] bg-[linear-gradient(160deg,#14352c_0%,#0b1f1a_55%,#081612_100%)] shadow-[0_40px_80px_rgba(0,0,0,0.35)]"
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(196,240,97,0.18),transparent_45%)]" />
            <div className="relative flex h-full flex-col justify-between p-6 sm:p-8">
              <div className="rounded-2xl border border-[var(--line)] bg-black/20 p-4 backdrop-blur">
                <div className="text-xs uppercase tracking-wider text-[var(--ink-muted)]">
                  Associate ask
                </div>
                <p className="mt-2 text-sm">
                  “Opened headphones — how many days to return?”
                </p>
              </div>
              <div className="ml-auto max-w-[85%] rounded-2xl border border-[var(--accent)]/30 bg-[var(--accent)]/10 p-4">
                <div className="text-xs uppercase tracking-wider text-[var(--accent)]">
                  ShelfMate · grounded
                </div>
                <p className="mt-2 text-sm leading-relaxed">
                  Opened electronics: <strong>15 days</strong>. Source:
                  Electronics Returns &amp; Exchanges.
                </p>
              </div>
              <div className="flex gap-2 text-xs text-[var(--ink-muted)]">
                <span className="rounded-full border border-[var(--line)] px-3 py-1">
                  MCP · search_policies
                </span>
                <span className="rounded-full border border-[var(--line)] px-3 py-1">
                  Ollama local
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[var(--line)] bg-black/20">
          <div className="mx-auto grid max-w-6xl gap-6 px-6 py-16 sm:grid-cols-2 lg:grid-cols-4">
            {CAPABILITIES.map((item) => (
              <article key={item.title} className="space-y-3">
                <item.icon className="h-6 w-6 text-[var(--accent)]" />
                <h2
                  className="text-lg"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {item.title}
                </h2>
                <p className="text-sm leading-relaxed text-[var(--ink-muted)]">
                  {item.desc}
                </p>
              </article>
            ))}
          </div>
        </section>

        <footer className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 text-sm text-[var(--ink-muted)] sm:flex-row sm:items-center sm:justify-between">
          <span>ShelfMate prototype for the Artefact take-home case.</span>
          <Link to="/login" className="text-[var(--accent)] hover:underline">
            Sign in to try the agent →
          </Link>
        </footer>
      </main>
    </div>
  );
}
