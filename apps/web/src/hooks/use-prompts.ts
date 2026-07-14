import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface PromptTemplate {
  name: string;
  content: string;
  isSystemPrompt: boolean;
}

export function usePrompts(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["prompts", tenantId],
    queryFn: () => api.get<PromptTemplate[]>(`/v1/admin/tenants/${tenantId}/prompts`),
    enabled: !!tenantId,
  });
}

export function useCreatePrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; content: string; is_system_prompt: boolean }) =>
      api.post(`/v1/admin/tenants/${tenantId}/prompts`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts", tenantId] });
    },
  });
}

export function useUpdatePrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, ...payload }: { name: string; content: string; is_system_prompt: boolean }) =>
      api.put(`/v1/admin/tenants/${tenantId}/prompts/${encodeURIComponent(name)}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts", tenantId] });
    },
  });
}

export function useDeletePrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.delete(`/v1/admin/tenants/${tenantId}/prompts/${encodeURIComponent(name)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prompts", tenantId] });
    },
  });
}

export function usePreviewPrompt(tenantId: string) {
  return useMutation({
    mutationFn: (payload: { name: string; query: string; context?: string }) =>
      api.post<{ messages: Array<{ role: string; content: string }> }>(
        `/v1/admin/tenants/${tenantId}/prompts/preview`, payload,
      ),
  });
}
