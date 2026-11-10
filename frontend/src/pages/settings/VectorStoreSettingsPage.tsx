/**
 * Weaviate connection status + reindex action.
 */
import { useEffect, useState } from "react";
import { LoaderCircle, RefreshCw } from "lucide-react";
import { settingsApi } from "@/api/settings";

export default function VectorStoreSettingsPage() {
  const [url, setUrl] = useState("http://127.0.0.1:8080");
  const [apiKey, setApiKey] = useState("");
  const [collection, setCollection] = useState("ShelfMatePolicyChunk");
  const [health, setHealth] = useState<Awaited<
    ReturnType<typeof settingsApi.vectorHealth>
  > | null>(null);
  const [busy, setBusy] = useState(false);
  const [reindexBusy, setReindexBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshHealth() {
    const h = await settingsApi.vectorHealth();
    setHealth(h);
  }

  useEffect(() => {
    void settingsApi.getModels().then((data) => {
      setUrl(data.vector_store.url);
      setCollection(data.vector_store.collection);
    });
    void refreshHealth().catch((err) =>
      setError(err instanceof Error ? err.message : "Health check failed"),
    );
  }, []);

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await settingsApi.saveModels({
        vector_store: {
          url: url.trim(),
          api_key: apiKey.trim(),
          collection: collection.trim(),
        } as never,
      });
      setApiKey("");
      setMessage("Vector store settings saved.");
      await refreshHealth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function reindex() {
    setReindexBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await settingsApi.reindex();
      setMessage(
        `Reindexed ${result.doc_count} docs → ${result.chunk_count} chunks with ${result.embedding_model} (${result.dimensions}d).`,
      );
      await refreshHealth();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reindex failed");
    } finally {
      setReindexBusy(false);
    }
  }

  return (
    <div className="max-w-xl space-y-4">
      <div>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)" }}>
          Vector store
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Local Weaviate via docker compose. Bring-your-own vectors from the embedding model.
        </p>
      </div>

      <label className="block text-sm text-[var(--ink-muted)]">
        url
        <input
          className="mt-1 w-full rounded-xl border border-[var(--line)] bg-black/20 px-3 py-2 text-sm"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        api_key
        <input
          className="mt-1 w-full rounded-xl border border-[var(--line)] bg-black/20 px-3 py-2 text-sm"
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="leave blank to keep"
        />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        collection
        <input
          className="mt-1 w-full rounded-xl border border-[var(--line)] bg-black/20 px-3 py-2 text-sm"
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
        />
      </label>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void save()}
          disabled={busy}
          className="btn-accent rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50"
          style={{ color: "#102016" }}
        >
          {busy ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={() => void reindex()}
          disabled={reindexBusy}
          className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] px-4 py-2 text-sm disabled:opacity-50"
        >
          {reindexBusy ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Reindex policies
        </button>
        <button
          type="button"
          onClick={() => void refreshHealth()}
          className="rounded-full border border-[var(--line)] px-4 py-2 text-sm"
        >
          Refresh health
        </button>
      </div>

      {message ? <p className="text-sm text-[var(--ok)]">{message}</p> : null}
      {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}

      <pre className="overflow-auto rounded-xl border border-[var(--line)] bg-black/20 p-3 text-xs text-[var(--ink-muted)]">
        {health ? JSON.stringify(health, null, 2) : "Checking Weaviate…"}
      </pre>

      <p className="text-xs text-[var(--ink-muted)]">
        Start Weaviate: <code>docker compose up -d</code> from the repo root.
      </p>
    </div>
  );
}
