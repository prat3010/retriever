import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export interface ClaimClassification {
  claim: string;
  premise: string;
  status: "entailment" | "neutral" | "contradiction";
  entailment_prob: number;
  contradiction_prob: number;
  neutral_prob: number;
}

export interface OnlineEvaluationLog {
  eval_id: string;
  tenant_id: string;
  session_id: string | null;
  message_id: string | null;
  query: string;
  answer: string;
  faithfulness: number;
  context_precision: number;
  hallucination_index: number;
  is_alert: boolean;
  claims: ClaimClassification[];
  created_at: string;
}

export interface OnlineEvaluationSummary {
  tenant_id: string;
  total_evaluations: number;
  avg_faithfulness: number;
  avg_context_precision: number;
  avg_hallucination_index: number;
  total_alerts: number;
}

export interface OnlineEvaluationLogsResponse {
  items: OnlineEvaluationLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface GroundingDiffResponse {
  tenant_id: string;
  total_claims: number;
  entailed_claims: number;
  contradicted_claims: number;
  neutral_claims: number;
  faithfulness_score: number;
  hallucination_index: number;
  claims: ClaimClassification[];
}

export function useOnlineEvaluationSummary(tenantId: string) {
  return useQuery<OnlineEvaluationSummary>({
    queryKey: ["online-evaluation-summary", tenantId],
    queryFn: () => api.get<OnlineEvaluationSummary>(`/v1/admin/tenants/${tenantId}/evaluation/online/summary`),
    enabled: !!tenantId,
  });
}

export function useOnlineEvaluationLogs(tenantId: string, limit = 20, offset = 0) {
  return useQuery<OnlineEvaluationLogsResponse>({
    queryKey: ["online-evaluation-logs", tenantId, limit, offset],
    queryFn: () =>
      api.get<OnlineEvaluationLogsResponse>(
        `/v1/admin/tenants/${tenantId}/evaluation/online/logs?limit=${limit}&offset=${offset}`
      ),
    enabled: !!tenantId,
  });
}

export function useOnlineEvaluationLog(tenantId: string, evalId: string | null) {
  return useQuery<OnlineEvaluationLog>({
    queryKey: ["online-evaluation-log", tenantId, evalId],
    queryFn: () => api.get<OnlineEvaluationLog>(`/v1/admin/tenants/${tenantId}/evaluation/online/logs/${evalId}`),
    enabled: !!tenantId && !!evalId,
  });
}

export const useHallucinationSummary = useOnlineEvaluationSummary;
