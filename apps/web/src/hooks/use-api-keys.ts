import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ApiKey {
  keyId: string;
  name: string;
  prefix: string;
  role: "admin" | "client";
  status: string;
  createdAt: string;
  expiresAt: string | null;
}

export interface CreateApiKeyPayload {
  name: string;
  role: "admin" | "client";
  expires_in_days?: number;
}

export interface CreatedApiKey {
  apiKey: string;
  keyId: string;
  tenantId: string;
  prefix: string;
  role: string;
  status: string;
}

export function useApiKeys(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["api-keys", tenantId],
    queryFn: () => api.get<ApiKey[]>(`/v1/admin/tenants/${tenantId}/api-keys`),
    enabled: !!tenantId,
  });
}

export function useCreateApiKey(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateApiKeyPayload) =>
      api.post<CreatedApiKey>(`/v1/admin/tenants/${tenantId}/api-keys`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-keys", tenantId] });
    },
  });
}

export function useRevokeApiKey(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      api.delete(`/v1/admin/tenants/${tenantId}/api-keys/${keyId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-keys", tenantId] });
    },
  });
}
