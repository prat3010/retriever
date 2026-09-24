import { api } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";

export interface ConfigureWebhookResponse {
  status: string;
  tenant_id: string;
  n8n_webhook_url: string;
  ping_result: {
    success: boolean;
    status_code?: number;
    error?: string;
  };
}

export type DAGNodeType =
  | "input"
  | "retrieval"
  | "guardrail"
  | "transform"
  | "prompt"
  | "llm"
  | "evaluator"
  | "router"
  | "output";

export interface DAGNode {
  id: string;
  type: DAGNodeType;
  title: string;
  description?: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
  input_keys?: string[];
  output_keys?: string[];
}

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string | null;
  target_handle?: string | null;
  condition?: string | null;
}

export interface WorkflowDAGGraph {
  id: string;
  name: string;
  description?: string;
  tenant_id?: string | null;
  nodes: DAGNode[];
  edges: DAGEdge[];
}

export interface DAGCompilerResult {
  graph_id: string;
  is_valid: boolean;
  topological_order: string[];
  parallel_stages: string[][];
  variable_bindings: Record<string, string[]>;
  warnings: string[];
  errors: string[];
}

export interface StepExecutionDetail {
  node_id: string;
  node_type: DAGNodeType;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  latency_ms: number;
  tokens_used: number;
  cost_usd: number;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface DAGExecutionResult {
  execution_id: string;
  tenant_id: string;
  graph_id: string;
  status: string;
  topological_order: string[];
  step_details: Record<string, StepExecutionDetail>;
  final_output: Record<string, unknown>;
  total_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  started_at: string;
  completed_at: string;
}

export function useConfigureN8nWebhook(tenantId: string) {
  return useMutation<ConfigureWebhookResponse, Error, string>({
    mutationFn: (n8n_webhook_url: string) =>
      api.post<ConfigureWebhookResponse>(`/v1/admin/tenants/${tenantId}/workflow/webhooks`, { n8n_webhook_url }),
  });
}

export function useN8nSpec() {
  return useQuery<Record<string, unknown>>({
    queryKey: ["n8n-spec"],
    queryFn: () => api.get<Record<string, unknown>>("/v1/workflow/n8n-spec"),
  });
}

export function useWorkflowTemplates(tenantId: string) {
  return useQuery<WorkflowDAGGraph[]>({
    queryKey: ["dag-templates", tenantId],
    queryFn: () => api.get<WorkflowDAGGraph[]>(`/v1/tenants/${tenantId}/workflows/dag/templates`),
    enabled: Boolean(tenantId),
  });
}

export function useCompileDAG(tenantId: string) {
  return useMutation<DAGCompilerResult, Error, WorkflowDAGGraph>({
    mutationFn: (graph: WorkflowDAGGraph) =>
      api.post<DAGCompilerResult>(`/v1/tenants/${tenantId}/workflows/dag/compile`, graph),
  });
}

export interface ExecuteDAGPayload {
  graph: WorkflowDAGGraph;
  input_payload: Record<string, unknown>;
}

export function useExecuteDAG(tenantId: string) {
  return useMutation<DAGExecutionResult, Error, ExecuteDAGPayload>({
    mutationFn: (payload: ExecuteDAGPayload) =>
      api.post<DAGExecutionResult>(`/v1/tenants/${tenantId}/workflows/dag/execute`, payload),
  });
}
