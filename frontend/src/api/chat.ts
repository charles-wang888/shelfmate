import { http } from "./http";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSource {
  doc_id: string;
  title: string;
}

export interface Citation {
  doc_id: string;
  title: string;
  chunk_id?: string;
  excerpt: string;
  similarity?: number;
  score?: number;
  confidence?: string;
  mode?: string;
}

export interface ToolCallTrace {
  name: string;
  arguments: Record<string, unknown>;
  result_preview: string;
}

export interface EscalationTicket {
  id: string;
  question: string;
  reason: string;
  store_id: string;
  priority: string;
  status: string;
  created_at: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  citations?: Citation[];
  confidence?: string | null;
  tool_calls: ToolCallTrace[];
  refused: boolean;
  escalation: EscalationTicket | null;
  model: string;
}

export const chatApi = {
  send: (messages: ChatMessage[], storeId: string) =>
    http.post<unknown, ChatResponse>("/chat", {
      messages,
      store_id: storeId,
    }),
  health: () => http.get("/health"),
};
