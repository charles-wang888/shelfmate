/**
 * Knowledge base browser — policy docs, chunks, and trial retrieval with scores.
 */
import { useEffect, useState } from "react";
import { LoaderCircle, Search } from "lucide-react";
import {
  knowledgeApi,
  type KnowledgeChunk,
  type KnowledgeDoc,
  type SearchHit,
} from "@/api/knowledge";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<{
    title: string;
    text: string;
    chunks: KnowledgeChunk[];
  } | null>(null);
  const [query, setQuery] = useState("opened electronics return window");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [mode, setMode] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void knowledgeApi
      .list()
      .then((data) => {
        setDocs(data.documents);
        if (data.documents[0]) setSelected(data.documents[0].doc_id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  useEffect(() => {
    if (!selected) return;
    void knowledgeApi
      .get(selected)
      .then((doc) =>
        setDetail({ title: doc.title, text: doc.text, chunks: doc.chunks }),
      )
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load doc"));
  }, [selected]);

  async function runSearch() {
    setBusy(true);
    setError(null);
    try {
      const data = await knowledgeApi.search(query, 5);
      setHits(data.results);
      setMode(data.mode || null);
      setWarning(data.warning || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
      <aside className="rounded-[1.5rem] border border-[var(--line)] bg-black/20 p-4">
        <h2 className="text-lg" style={{ fontFamily: "var(--font-display)" }}>
          Policy library
        </h2>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">
          Browse NovaMart documents and their indexed chunks.
        </p>
        <div className="mt-4 space-y-2">
          {docs.map((doc) => (
            <button
              key={doc.doc_id}
              type="button"
              onClick={() => setSelected(doc.doc_id)}
              className={`block w-full rounded-xl border px-3 py-2 text-left text-sm ${
                selected === doc.doc_id
                  ? "border-[var(--accent)] bg-[var(--accent)]/10"
                  : "border-[var(--line)] hover:border-[var(--accent)]/50"
              }`}
            >
              <div className="font-medium">{doc.title}</div>
              <div className="text-[11px] text-[var(--ink-muted)]">
                {doc.chunk_count} chunks · {doc.doc_id}
              </div>
            </button>
          ))}
        </div>
      </aside>

      <div className="space-y-4">
        <section className="rounded-[1.5rem] border border-[var(--line)] bg-[var(--bg-elevated)]/70 p-5">
          <h3 className="text-base" style={{ fontFamily: "var(--font-display)" }}>
            Trial retrieval
          </h3>
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            Runs the same MCP `search_policies` path used by the agent (Weaviate + embeddings).
          </p>
          <div className="mt-3 flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 rounded-full border border-[var(--line)] bg-black/20 px-4 py-2 text-sm outline-none ring-[var(--accent)] focus:ring-2"
            />
            <button
              type="button"
              onClick={() => void runSearch()}
              disabled={busy || !query.trim()}
              className="btn-accent inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50"
              style={{ color: "#102016" }}
            >
              {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Search
            </button>
          </div>
          {mode ? (
            <p className="mt-2 text-xs text-[var(--ink-muted)]">Mode: {mode}</p>
          ) : null}
          {warning ? <p className="mt-1 text-xs text-[var(--warm)]">{warning}</p> : null}
          <div className="mt-3 space-y-2">
            {hits.map((hit, i) => (
              <article
                key={`${hit.chunk_id || hit.doc_id}-${i}`}
                className="rounded-xl border border-[var(--line)] bg-black/20 p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <strong>{hit.title || hit.doc_id}</strong>
                  {hit.confidence ? (
                    <span className="rounded-full border border-[var(--line)] px-2 py-0.5 capitalize">
                      {hit.confidence}
                      {typeof hit.similarity === "number"
                        ? ` · ${(hit.similarity * 100).toFixed(0)}%`
                        : ""}
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-xs text-[var(--ink-muted)] whitespace-pre-wrap">
                  {hit.excerpt}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-[1.5rem] border border-[var(--line)] bg-[var(--bg-elevated)]/70 p-5">
          {error ? <p className="mb-3 text-sm text-[var(--danger)]">{error}</p> : null}
          {detail ? (
            <>
              <h3 className="text-xl" style={{ fontFamily: "var(--font-display)" }}>
                {detail.title}
              </h3>
              <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-[var(--line)] bg-black/20 p-4 text-xs leading-relaxed text-[var(--ink-muted)]">
                {detail.text}
              </pre>
              <h4 className="mt-6 text-sm uppercase tracking-wide text-[var(--ink-muted)]">
                Chunks ({detail.chunks.length})
              </h4>
              <div className="mt-3 space-y-2">
                {detail.chunks.map((chunk) => (
                  <details
                    key={chunk.chunk_id}
                    className="rounded-xl border border-[var(--line)] bg-black/15 px-3 py-2 text-sm"
                  >
                    <summary className="cursor-pointer text-xs text-[var(--ink-muted)]">
                      {chunk.chunk_id}
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap text-xs">{chunk.text}</p>
                  </details>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-[var(--ink-muted)]">Select a document.</p>
          )}
        </section>
      </div>
    </div>
  );
}
