import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ToolDefinition {
  name: string;
  description: string;
  parameters_schema?: Record<string, any>;
  category?: string;
  requires_approval: boolean;
  risk_level: "low" | "medium" | "high" | "critical";
}

export interface HITLApprovalRequest {
  action_id: string;
  thread_id: string;
  tenant_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  risk_level: "low" | "medium" | "high" | "critical";
  description: string;
  status: "pending" | "approved" | "rejected";
  created_at: number;
}

export interface ThreadCheckpointItem {
  checkpoint_id: string;
  thread_id: string;
  tenant_id: string;
  node_name: string;
  step_index: number;
  state_snapshot: Record<string, any>;
  created_at: number;
}

export interface ThreadHistoryResponse {
  thread_id: string;
  tenant_id: string;
  total_checkpoints: number;
  checkpoints: ThreadCheckpointItem[];
}

export interface AgentExecutionResult {
  tenant_id: string;
  thread_id: string;
  prompt: string;
  final_answer: string;
  status: "completed" | "waiting_approval" | "rejected" | "error";
  steps: Array<{
    step_index: number;
    thought: string;
    tool_calls: Array<{ call_id: string; tool_name: string; arguments: Record<string, any> }>;
    tool_results: Array<{ call_id: string; tool_name: string; output: any; is_error: boolean }>;
  }>;
  pending_approval?: HITLApprovalRequest | null;
  checkpoint_id?: string | null;
  total_steps: number;
  execution_time_ms: number;
}

function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("retriever_admin_key") || "dev-admin-master-key-change-in-production";
}

export function useAgentTools(tenantId: string) {
  return useQuery<ToolDefinition[]>({
    queryKey: ["agentic", "tools", tenantId],
    queryFn: async () => {
      if (!tenantId) return [];
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/agentic/tools`, {
        headers: { "X-Admin-Master-Key": getAdminKey() },
      });
      if (!res.ok) throw new Error("Failed to fetch agent tools");
      return res.json();
    },
    enabled: !!tenantId,
    staleTime: 60_000,
  });
}

export function useThreadHistory(tenantId: string, threadId: string) {
  return useQuery<ThreadHistoryResponse>({
    queryKey: ["agentic", "history", tenantId, threadId],
    queryFn: async () => {
      if (!tenantId || !threadId) return { thread_id: "", tenant_id: "", total_checkpoints: 0, checkpoints: [] };
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/agentic/threads/${threadId}/history`, {
        headers: { "X-Admin-Master-Key": getAdminKey() },
      });
      if (!res.ok) throw new Error("Failed to fetch thread checkpoint history");
      return res.json();
    },
    enabled: !!tenantId && !!threadId,
  });
}

export function useExecuteWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<
    AgentExecutionResult,
    Error,
    { tenantId: string; prompt: string; threadId?: string; maxSteps?: number; allowedTools?: string[] }
  >({
    mutationFn: async ({ tenantId, prompt, threadId, maxSteps = 10, allowedTools }) => {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/agentic/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Master-Key": getAdminKey(),
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          prompt,
          thread_id: threadId,
          max_steps: maxSteps,
          allowed_tools: allowedTools,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Execution failed" }));
        throw new Error(err.detail || "Agent execution failed");
      }
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agentic", "history", data.tenant_id, data.thread_id] });
    },
  });
}

export function useResumeWorkflow() {
  const queryClient = useQueryClient();
  return useMutation<
    AgentExecutionResult,
    Error,
    {
      tenantId: string;
      threadId: string;
      actionId: string;
      decision: "approve" | "reject";
      modifiedArguments?: Record<string, any>;
      comment?: string;
    }
  >({
    mutationFn: async ({ tenantId, threadId, actionId, decision, modifiedArguments, comment }) => {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/agentic/threads/${threadId}/resume`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Master-Key": getAdminKey(),
        },
        body: JSON.stringify({
          action_id: actionId,
          decision,
          modified_arguments: modifiedArguments,
          comment,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Resume failed" }));
        throw new Error(err.detail || "Failed to resume thread");
      }
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["agentic", "history", data.tenant_id, data.thread_id] });
    },
  });
}

export function useRollbackThread() {
  const queryClient = useQueryClient();
  return useMutation<
    ThreadCheckpointItem,
    Error,
    { tenantId: string; threadId: string; checkpointId: string; fork?: boolean }
  >({
    mutationFn: async ({ tenantId, threadId, checkpointId, fork = false }) => {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/agentic/threads/${threadId}/rollback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Master-Key": getAdminKey(),
        },
        body: JSON.stringify({
          target_checkpoint_id: checkpointId,
          fork,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Rollback failed" }));
        throw new Error(err.detail || "Rollback failed");
      }
      return res.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["agentic", "history", variables.tenantId, variables.threadId] });
    },
  });
}
