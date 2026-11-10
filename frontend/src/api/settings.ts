import { http } from "./http";

export interface LlmSettings {
  provider: string;
  model: string;
  base_url: string;
  api_key: string;
  api_key_set?: boolean;
  api_key_hint?: string;
  timeout_seconds: number;
}

export interface EmbeddingSettings {
  provider: string;
  model: string;
  base_url: string;
  api_key: string;
  api_key_set?: boolean;
  api_key_hint?: string;
  dimensions: number;
}

export interface VectorStoreSettings {
  url: string;
  api_key: string;
  api_key_set?: boolean;
  api_key_hint?: string;
  collection: string;
}

export interface ModelSettings {
  llm: LlmSettings;
  embedding: EmbeddingSettings;
  vector_store: VectorStoreSettings;
  providers: { llm: string[]; embedding: string[] };
}

export interface VectorHealth {
  ok: boolean;
  url?: string;
  collection?: string;
  collection_exists?: boolean;
  object_count?: number;
  error?: string;
}

export interface ReindexResult {
  ok: boolean;
  chunk_count: number;
  doc_count: number;
  embedding_model: string;
  dimensions: number;
}

export const settingsApi = {
  getModels: () => http.get<unknown, ModelSettings>("/settings/models"),
  saveModels: (body: Partial<ModelSettings>) =>
    http.put<unknown, ModelSettings>("/settings/models", body),
  vectorHealth: () =>
    http.get<unknown, VectorHealth>("/settings/vector-store/health"),
  reindex: () =>
    http.post<unknown, ReindexResult>("/settings/vector-store/reindex"),
};
