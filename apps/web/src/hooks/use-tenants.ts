import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Tenant {
  tenantId: string;
  name: string;
  status: string;
  tier: string;
  createdAt: string;
}

export interface PaginatedTenants {
  items: Tenant[];
  total: number;
}

export function useTenants(search?: string, limit = 50, offset = 0) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  return useQuery({
    queryKey: ["tenants", search, limit, offset],
    queryFn: () => api.get<PaginatedTenants>(`/v1/admin/tenants?${params}`),
  });
}

export function useAllTenants(limit = 50) {
  return useQuery({
    queryKey: ["tenants", "all", limit],
    queryFn: () => api.get<PaginatedTenants>(`/v1/admin/tenants?limit=${limit}`),
  });
}

export function useTenant(id: string | undefined) {
  return useQuery({
    queryKey: ["tenants", id],
    queryFn: () => api.get<Tenant>(`/v1/admin/tenants/${id}`),
    enabled: !!id,
  });
}

export function useDeactivateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/v1/admin/tenants/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
    },
  });
}

export interface CreateTenantPayload {
  name: string;
  tier?: string;
  isolation_level?: string;
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTenantPayload) =>
      api.post<Tenant>("/v1/tenants", payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
    },
  });
}
