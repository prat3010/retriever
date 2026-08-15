import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export interface HallucinationSummary {
  tenant_id: string;
  total_evaluations: number;
  avg_faithfulness: number;
  avg_context_relevance: number;
  unfaithful_count: number;
  min_faithfulness_threshold: number;
  evaluations: Array<{
    evaluation_id: string;
    session_id: string;
    message_id: string;
    faithfulness_score: number;
    context_relevance_score: number;
    is_hallucination: boolean;
    created_at: string;
  }>;
}

export function useHallucinationSummary(tenantId: string) {
  return useQuery<HallucinationSummary>({
    queryKey: ["hallucinations", tenantId],
    queryFn: () => api.get<HallucinationSummary>(`/v1/admin/tenants/${tenantId}/evaluations/summary`),
    enabled: !!tenantId,
  });
}
