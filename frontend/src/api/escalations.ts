import { http } from "./http";
import type { ChatMessage, EscalationTicket } from "./chat";

export const escalationsApi = {
  list: (status = "open") =>
    http.get<unknown, { count: number; tickets: EscalationTicket[] }>(
      `/escalations`,
      { params: { status } },
    ),
  create: (body: {
    question: string;
    reason: string;
    store_id: string;
    context: ChatMessage[];
  }) =>
    http.post<unknown, { created: boolean; ticket: EscalationTicket }>(
      "/escalations",
      body,
    ),
  resolve: (ticketId: string) =>
    http.post(`/escalations/${ticketId}/resolve`),
};
