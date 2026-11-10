import { http } from "./http";

export interface KnowledgeDoc {
  doc_id: string;
  title: string;
  chunk_count: number;
}

export interface KnowledgeChunk {
  chunk_id: string;
  doc_id: string;
  title: string;
  chunk_index: number;
  text: string;
}

export interface SearchHit {
  doc_id: string;
  title: string;
  chunk_id?: string;
  excerpt: string;
  similarity?: number;
  score?: number;
  confidence?: string;
}

export const knowledgeApi = {
  list: () =>
    http.get<unknown, { count: number; documents: KnowledgeDoc[] }>(
      "/knowledge/documents",
    ),
  get: (docId: string) =>
    http.get<
      unknown,
      { doc_id: string; title: string; text: string; chunks: KnowledgeChunk[] }
    >(`/knowledge/documents/${docId}`),
  search: (q: string, limit = 5) =>
    http.get<
      unknown,
      { query: string; count: number; mode?: string; results: SearchHit[]; warning?: string }
    >("/knowledge/search", { params: { q, limit } }),
};
