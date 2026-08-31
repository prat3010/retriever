import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

export interface TenantLiveTelemetry {
  tenant_id: string;
  monthly_tokens_used: number;
  documents_count: number;
  storage_bytes_used: number;
  cache_hits: number;
  latency_saved_ms: number;
  cost_saved_usd: number;
  thumbs_up: number;
  thumbs_down: number;
  satisfaction_rate: number;
  avg_faithfulness: number;
  avg_precision: number;
  hallucination_index: number;
  p99_latency_ms: number;
}

export function useLiveTelemetry(tenantId: string) {
  return useQuery<TenantLiveTelemetry>({
    queryKey: ["live-telemetry", tenantId],
    queryFn: () => api.get<TenantLiveTelemetry>(`/v1/admin/tenants/${tenantId}/telemetry/live`),
    enabled: !!tenantId,
    refetchInterval: 15_000, // auto-refresh every 15s for live cockpit monitoring
  });
}
