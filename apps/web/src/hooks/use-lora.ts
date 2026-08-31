import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface LoraAdapter {
  adapter_id: string;
  tenant_id: string;
  name: string;
  domain_tag: string;
  rank: number;
  loss_score: number | null;
  created_at: string;
}

export interface LoraTrainPayload {
  name: string;
  domain_tag: string;
  rank: number;
  epochs: number;
  learning_rate: number;
  pairs?: Array<{ query: string; positive_chunk: string }>;
}

export interface LoraTrainResult {
  adapter_id: string;
  tenant_id: string;
  name: string;
  rank: number;
  loss_score: number;
  message: string;
}

export function useLoraAdapters(tenantId: string | undefined) {
  return useQuery<LoraAdapter[]>({
    queryKey: ["lora-adapters", tenantId],
    queryFn: () => api.get<LoraAdapter[]>(`/v1/admin/tenants/${tenantId}/lora/adapters`),
    enabled: !!tenantId,
  });
}

export function useTrainLoraAdapter(tenantId: string) {
  const qc = useQueryClient();
  return useMutation<LoraTrainResult, Error, LoraTrainPayload>({
    mutationFn: (payload) => api.post(`/v1/admin/tenants/${tenantId}/lora/train`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lora-adapters", tenantId] });
      qc.invalidateQueries({ queryKey: ["config", tenantId] });
    },
  });
}

export function useActivateLoraAdapter(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (adapterId: string) =>
      api.post(`/v1/admin/tenants/${tenantId}/lora/adapters/${adapterId}/activate`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config", tenantId] });
      qc.invalidateQueries({ queryKey: ["lora-adapters", tenantId] });
    },
  });
}
