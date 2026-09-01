import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface CodeExecutionRecord {
  script?: string;
  output?: string;
  return_value?: unknown;
  is_error?: boolean;
  error_message?: string | null;
  execution_time_ms?: number;
}

export interface RlmAnalysisRequest {
  tenant_id?: string;
  prompt: string;
  document_ids?: string[];
  max_depth?: number;
}

export interface RlmAnalysisResult {
  tenant_id: string;
  prompt: string;
  analysis_summary: string;
  code_executions: CodeExecutionRecord[];
  subcalls_count: number;
  execution_time_ms: number;
}

export interface ConsensusRequest {
  tenant_id?: string;
  prompt: string;
  generator_provider_name?: string;
  critic_provider_name?: string;
  max_reflection_rounds?: number;
}

export interface ReflectionHistoryItem {
  round: number;
  draft_response: string;
  critic_approved: boolean;
  critique_score: number;
  critique_feedback: string;
  unsupported_claims: string[];
}

export interface ConsensusResult {
  tenant_id: string;
  prompt: string;
  final_response: string;
  generator_used: string;
  critic_used: string;
  approved_on_round: number;
  reflection_history: ReflectionHistoryItem[];
  execution_time_ms: number;
}

export function useRlmAnalysisMutation(tenantId: string | undefined) {
  return useMutation({
    mutationFn: (req: { prompt: string; document_ids?: string[]; max_depth?: number }) =>
      api.post<RlmAnalysisResult>(`/v1/tenants/${tenantId}/rlm/analyze`, {
        tenant_id: tenantId,
        prompt: req.prompt,
        document_ids: req.document_ids,
        max_depth: req.max_depth ?? 3,
      }),
  });
}

export function useConsensusMutation(tenantId: string | undefined) {
  return useMutation({
    mutationFn: (req: {
      prompt: string;
      generator_provider_name?: string;
      critic_provider_name?: string;
      max_reflection_rounds?: number;
    }) =>
      api.post<ConsensusResult>(`/v1/tenants/${tenantId}/consensus/generate`, {
        tenant_id: tenantId,
        prompt: req.prompt,
        generator_provider_name: req.generator_provider_name || undefined,
        critic_provider_name: req.critic_provider_name || undefined,
        max_reflection_rounds: req.max_reflection_rounds ?? 2,
      }),
  });
}
