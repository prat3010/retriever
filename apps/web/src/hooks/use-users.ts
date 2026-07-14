import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface User {
  userId: string;
  tenantId: string;
  externalId: string;
  displayName: string | null;
  isActive: boolean;
  createdAt: string;
}

export interface CreateUserPayload {
  external_id: string;
  display_name?: string;
}

export function useUsers(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["users", tenantId],
    queryFn: () => api.get<User[]>(`/v1/admin/tenants/${tenantId}/users`),
    enabled: !!tenantId,
  });
}

export function useCreateUser(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserPayload) =>
      api.post<User>(`/v1/admin/tenants/${tenantId}/users`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users", tenantId] });
    },
  });
}
