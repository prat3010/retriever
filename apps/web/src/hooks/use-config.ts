import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface TenantConfig {
  tenant_id: string;
  ai_provider: {
    provider_name: string;
    api_key: string | null;
    base_url: string | null;
    default_model: string;
  };
  retrieval_settings: {
    top_k: number;
    rrf_k: number;
    reranking_threshold: number;
  };
  feature_flags: Record<string, boolean>;
  security_settings: {
    enable_rls: boolean;
    api_key_expiration_days: number;
  };
}

export function useConfig(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["config", tenantId],
    queryFn: () => api.get<TenantConfig>(`/v1/admin/tenants/${tenantId}/config`),
    enabled: !!tenantId,
  });
}

export function useUpdateConfig(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: TenantConfig) =>
      api.put(`/v1/admin/tenants/${tenantId}/config`, config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config", tenantId] });
    },
  });
}
