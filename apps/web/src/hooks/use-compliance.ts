import { api } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export interface AnonymizeTestRequest {
  text: string;
}

export interface AnonymizeTestResponse {
  original_text: string;
  anonymized_text: string;
  pii_detected_count: number;
}

export interface PurgeTenantResponse {
  status: string;
  tenant_id: string;
  deleted_documents: number;
  deleted_chunks: number;
  deleted_vectors: number;
}

export function useAnonymizeTest(tenantId: string) {
  return useMutation<AnonymizeTestResponse, Error, string>({
    mutationFn: (text: string) =>
      api.post<AnonymizeTestResponse>(`/v1/admin/tenants/${tenantId}/compliance/anonymize`, { text }),
  });
}

export function usePurgeTenantData(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<PurgeTenantResponse, Error, void>({
    mutationFn: () =>
      api.post<PurgeTenantResponse>(`/v1/admin/tenants/${tenantId}/compliance/forget`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["tenants", tenantId] });
    },
  });
}

export function useRunRetentionPurge(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<{ status: string; purged_count: number }, Error, void>({
    mutationFn: () =>
      api.post<{ status: string; purged_count: number }>(`/v1/admin/tenants/${tenantId}/compliance/run-retention-purge`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
    },
  });
}
