/**
 * Chat model + Embedding settings forms (field layout inspired by KE).
 */
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { settingsApi, type ModelSettings } from "@/api/settings";

const inputClass =
  "mt-1 w-full rounded-xl border border-[var(--line)] bg-black/20 px-3 py-2 text-sm outline-none ring-[var(--accent)] focus:ring-2";

function Frame({
  title,
  description,
  children,
  onSubmit,
  busy,
  saved,
  error,
}: {
  title: string;
  description: string;
  children: ReactNode;
  onSubmit: (e: FormEvent) => void;
  busy: boolean;
  saved: boolean;
  error: string | null;
}) {
  return (
    <form onSubmit={onSubmit} className="max-w-xl space-y-4">
      <div>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)" }}>
          {title}
        </h1>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">{description}</p>
      </div>
      {children}
      {error ? <p className="text-sm text-[var(--danger)]">{error}</p> : null}
      {saved ? (
        <p className="text-sm text-[var(--ok)]">Saved — takes effect immediately.</p>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className="btn-accent rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50"
        style={{ color: "#102016" }}
      >
        {busy ? "Saving…" : "Save"}
      </button>
    </form>
  );
}

export function ChatModelSettingsPage() {
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(120);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void settingsApi.getModels().then((data) => {
      setSettings(data);
      setProvider(data.llm.provider || "ollama");
      setModel(data.llm.model);
      setBaseUrl(data.llm.base_url);
      setTimeoutSeconds(data.llm.timeout_seconds);
    }).catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      const next = await settingsApi.saveModels({
        llm: {
          provider,
          model: model.trim(),
          base_url: baseUrl.trim(),
          api_key: apiKey.trim(),
          timeout_seconds: timeoutSeconds,
        } as ModelSettings["llm"],
      });
      setSettings(next);
      setApiKey("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Frame
      title="Chat model"
      description="Affects Q&A only. Default: DeepSeek deepseek-chat. Leave API key blank to keep the previous secret."
      onSubmit={onSubmit}
      busy={busy}
      saved={saved}
      error={error}
    >
      <label className="block text-sm text-[var(--ink-muted)]">
        provider
        <select className={inputClass} value={provider} onChange={(e) => setProvider(e.target.value)}>
          {(settings?.providers.llm || ["ollama", "openai", "anthropic", "google"]).map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        model
        <input className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} placeholder="qwen3:8b" />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        base_url
        <input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://127.0.0.1:11434" />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        api_key {settings?.llm.api_key_set ? `(${settings.llm.api_key_hint})` : ""}
        <input
          className={inputClass}
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="leave blank to keep"
          autoComplete="off"
        />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        timeout_seconds
        <input
          className={inputClass}
          type="number"
          value={timeoutSeconds}
          onChange={(e) => setTimeoutSeconds(Number(e.target.value) || 120)}
        />
      </label>
    </Frame>
  );
}

export function EmbeddingSettingsPage() {
  const [settings, setSettings] = useState<ModelSettings | null>(null);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("qwen3-embedding");
  const [baseUrl, setBaseUrl] = useState("http://127.0.0.1:11434");
  const [apiKey, setApiKey] = useState("");
  const [dimensions, setDimensions] = useState(1024);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void settingsApi.getModels().then((data) => {
      setSettings(data);
      setProvider(data.embedding.provider || "ollama");
      setModel(data.embedding.model);
      setBaseUrl(data.embedding.base_url);
      setDimensions(data.embedding.dimensions);
    }).catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      const next = await settingsApi.saveModels({
        embedding: {
          provider,
          model: model.trim(),
          base_url: baseUrl.trim(),
          api_key: apiKey.trim(),
          dimensions,
        } as ModelSettings["embedding"],
      });
      setSettings(next);
      setApiKey("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Frame
      title="Embedding model"
      description="Used to vectorize policy chunks and queries. Default: Tencent TokenHub kinfra-text-embedding-0.6b (1024d). Re-index after changing model/dimensions."
      onSubmit={onSubmit}
      busy={busy}
      saved={saved}
      error={error}
    >
      <label className="block text-sm text-[var(--ink-muted)]">
        provider
        <select className={inputClass} value={provider} onChange={(e) => setProvider(e.target.value)}>
          {(settings?.providers.embedding || ["ollama", "openai"]).map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        model
        <input className={inputClass} value={model} onChange={(e) => setModel(e.target.value)} />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        base_url
        <input className={inputClass} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        api_key {settings?.embedding.api_key_set ? `(${settings.embedding.api_key_hint})` : ""}
        <input
          className={inputClass}
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="ollama / leave blank to keep"
          autoComplete="off"
        />
      </label>
      <label className="block text-sm text-[var(--ink-muted)]">
        dimensions
        <input
          className={inputClass}
          type="number"
          value={dimensions}
          onChange={(e) => setDimensions(Number(e.target.value) || 1024)}
        />
      </label>
    </Frame>
  );
}
