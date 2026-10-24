import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ChatSessionSummary {
  session_id: string;
  tenant_id: string;
  user_id?: string | null;
  created_at: string;
  updated_at?: string | null;
  message_count: number;
  first_message_snippet?: string | null;
  last_message_snippet?: string | null;
}

export interface ChatMessageItem {
  role: "user" | "assistant" | "system";
  content: string;
  name?: string | null;
  created_at?: string;
}

export function useChatSessions(tenantId: string | undefined, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ["chat-sessions", tenantId, limit, offset],
    queryFn: () =>
      api.get<ChatSessionSummary[]>(
        `/v1/admin/tenants/${tenantId}/chat/sessions?limit=${limit}&offset=${offset}`
      ),
    enabled: !!tenantId,
    refetchInterval: 10_000,
  });
}

export function useChatSessionMessages(tenantId: string | undefined, sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-session-messages", tenantId, sessionId],
    queryFn: () =>
      api.get<ChatMessageItem[]>(
        `/v1/admin/tenants/${tenantId}/chat/sessions/${sessionId}/messages`
      ),
    enabled: !!tenantId && !!sessionId,
    refetchInterval: 5_000,
  });
}
