/**
 * Authenticated workspace — route `/app`.
 * Chat transcript, tool/source chips, escalate CTA, Ops ticket panel.
 */
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  LifeBuoy,
  LoaderCircle,
  LogOut,
  Send,
  Sparkles,
} from "lucide-react";

import { chatApi, type ChatMessage, type ChatResponse } from "@/api/chat";
import { escalationsApi } from "@/api/escalations";
import type { EscalationTicket } from "@/api/chat";
import { logout, useAuth } from "@/lib/auth";

interface UiMessage extends ChatMessage {
  meta?: ChatResponse;
}

const SUGGESTIONS = [
  "What is the return window for opened electronics?",
  "Where is order ORD-10042?",
  "Can we price match a local competitor flyer?",
  "What is the CEO's personal mobile number?",
];

export default function WorkspaceApp() {
  const { displayName, username } = useAuth();
  const [storeId, setStoreId] = useState("NM-204");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([
    {
      role: "assistant",
      content:
        "Hi — I'm ShelfMate. Ask about NovaMart policies, look up an order like ORD-10042, or escalate anything I cannot answer.",
    },
  ]);
  const [tickets, setTickets] = useState<EscalationTicket[]>([]);

  const lastAssistant = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return messages[i];
    }
    return null;
  }, [messages]);

  async function refreshTickets() {
    try {
      const data = await escalationsApi.list("open");
      setTickets(data.tickets);
    } catch {
      /* panel is best-effort */
    }
  }

  useEffect(() => {
    void refreshTickets();
  }, []);

  async function sendQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;

    const nextMessages: UiMessage[] = [
      ...messages,
      { role: "user", content: trimmed },
    ];
    setMessages(nextMessages);
    setInput("");
    setBusy(true);
    setError(null);

    try {
      const history = nextMessages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map(({ role, content }) => ({ role, content }));
      const result = await chatApi.send(history, storeId);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, meta: result },
      ]);
      if (result.escalation) {
        await refreshTickets();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await sendQuestion(input);
  }

  async function escalateLast() {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    setBusy(true);
    setError(null);
    try {
      await escalationsApi.create({
        question: lastUser.content,
        reason: "Associate requested Ops follow-up from workspace",
        store_id: storeId,
        context: messages.slice(-6).map(({ role, content }) => ({ role, content })),
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Escalation created for Ops. They can see your question and recent context in the side panel.",
        },
      ]);
      await refreshTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Escalate failed");
    } finally {
      setBusy(false);
    }
  }

  async function resolveTicket(id: string) {
    await escalationsApi.resolve(id);
    await refreshTickets();
  }

  function onLogout() {
    logout();
    window.location.assign("/");
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] pb-4">
        <div className="flex items-center gap-3">
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
              {displayName || username} · store{" "}
              <select
                className="rounded border border-[var(--line)] bg-transparent px-1"
                value={storeId}
                onChange={(e) => setStoreId(e.target.value)}
              >
                <option value="NM-204">NM-204</option>
                <option value="NM-118">NM-118</option>
                <option value="NM-055">NM-055</option>
              </select>
            </div>
          </div>
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

      <div className="grid flex-1 gap-4 lg:grid-cols-[1fr_300px]">
        <section className="flex min-h-[70vh] flex-col rounded-[1.5rem] border border-[var(--line)] bg-[var(--bg-elevated)]/70">
          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
            {messages.map((msg, idx) => (
              <article
                key={`${msg.role}-${idx}`}
                className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "ml-auto bg-[var(--accent)]"
                    : "bg-black/25 text-[var(--ink)]"
                }`}
                style={
                  msg.role === "user" ? { color: "#102016" } : undefined
                }
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.meta ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {msg.meta.refused ? (
                      <span className="rounded-full bg-[var(--danger)]/15 px-2 py-0.5 text-[11px] text-[var(--danger)]">
                        refused / unsure
                      </span>
                    ) : null}
                    {msg.meta.sources.map((s) => (
                      <span
                        key={s.doc_id}
                        className="rounded-full border border-[var(--line)] px-2 py-0.5 text-[11px] text-[var(--ink-muted)]"
                      >
                        {s.title || s.doc_id}
                      </span>
                    ))}
                    {msg.meta.tool_calls.map((t, i) => (
                      <span
                        key={`${t.name}-${i}`}
                        className="rounded-full border border-[var(--accent)]/30 px-2 py-0.5 text-[11px] text-[var(--accent)]"
                      >
                        MCP · {t.name}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
            {busy ? (
              <div className="inline-flex items-center gap-2 text-sm text-[var(--ink-muted)]">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Thinking with Ollama + MCP…
              </div>
            ) : null}
            {error ? (
              <p className="text-sm text-[var(--danger)]" role="alert">
                {error}
              </p>
            ) : null}
          </div>

          <div className="border-t border-[var(--line)] p-4">
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={busy}
                  onClick={() => void sendQuestion(s)}
                  className="rounded-full border border-[var(--line)] px-3 py-1 text-left text-xs text-[var(--ink-muted)] hover:border-[var(--accent)] hover:text-[var(--ink)] disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>

            <div className="mb-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || !messages.some((m) => m.role === "user")}
                onClick={() => void escalateLast()}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--warm)]/40 px-3 py-1.5 text-xs text-[var(--warm)] hover:bg-[var(--warm)]/10 disabled:opacity-40"
              >
                <LifeBuoy className="h-3.5 w-3.5" />
                Escalate to Ops
              </button>
              {lastAssistant?.meta?.refused ? (
                <span className="inline-flex items-center gap-1 text-xs text-[var(--ink-muted)]">
                  <Sparkles className="h-3.5 w-3.5" />
                  Last answer was unsure — escalate closes the loop.
                </span>
              ) : null}
            </div>

            <form onSubmit={onSubmit} className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about returns, orders, warranties…"
                className="flex-1 rounded-full border border-[var(--line)] bg-black/20 px-4 py-3 text-sm outline-none ring-[var(--accent)] focus:ring-2"
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="btn-accent inline-flex items-center gap-2 rounded-full px-4 py-3 text-sm font-semibold disabled:opacity-50"
                style={{ color: "#102016" }}
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </form>
          </div>
        </section>

        <aside className="rounded-[1.5rem] border border-[var(--line)] bg-black/20 p-4">
          <h2
            className="text-base"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Open Ops tickets
          </h2>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            Creative loop-closer: unresolved floor questions become actionable
            escalations.
          </p>
          <div className="mt-4 space-y-3">
            {tickets.length === 0 ? (
              <p className="text-sm text-[var(--ink-muted)]">No open tickets.</p>
            ) : (
              tickets.map((t) => (
                <article
                  key={t.id}
                  className="rounded-xl border border-[var(--line)] bg-[var(--bg-soft)]/40 p-3"
                >
                  <div className="flex items-center justify-between gap-2 text-[11px] text-[var(--ink-muted)]">
                    <span>{t.id}</span>
                    <span>{t.store_id}</span>
                  </div>
                  <p className="mt-2 text-sm">{t.question}</p>
                  <p className="mt-1 text-xs text-[var(--ink-muted)]">{t.reason}</p>
                  <button
                    type="button"
                    onClick={() => void resolveTicket(t.id)}
                    className="mt-3 text-xs text-[var(--ok)] hover:underline"
                  >
                    Mark resolved
                  </button>
                </article>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
