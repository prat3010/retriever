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

// ── Milestone 92: DSPy Declarative Prompt Compilation ────

export interface FewShotDemonstration {
  question: string;
  context: string;
  thought?: string | null;
  answer: string;
  score?: number;
}

export interface CompiledPromptProgram {
  program_id: string;
  tenant_id: string;
  name: string;
  signature_name: string;
  optimizer: string;
  dataset_id?: string | null;
  baseline_score: number;
  compiled_score: number;
  improvement_pct: number;
  metric_name: string;
  compiled_instruction: string;
  few_shot_demos: FewShotDemonstration[];
  is_active: boolean;
  created_at: string;
}

export interface PromptCompilationRequest {
  name?: string;
  dataset_id?: string | null;
  optimizer?: "BootstrapFewShot" | "MIPROv2" | "RandomSearch";
  max_demos?: number;
  metric_target?: "faithfulness" | "context_relevance" | "composite";
  train_data?: Array<{
    question: string;
    context: string;
    ground_truth_answer: string;
  }>;
  val_data?: Array<{
    question: string;
    context: string;
    ground_truth_answer: string;
  }>;
}

export interface PromptCompilationResult {
  program_id: string;
  tenant_id: string;
  name: string;
  signature_name: string;
  optimizer: string;
  dataset_id?: string | null;
  baseline_score: number;
  compiled_score: number;
  improvement_pct: number;
  metric_name: string;
  compiled_instruction: string;
  few_shot_demos: FewShotDemonstration[];
  is_active: boolean;
  created_at: string;
}

export function useCompiledPrompts(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["compiled-prompts", tenantId],
    queryFn: () => api.get<CompiledPromptProgram[]>(`/v1/tenants/${tenantId}/prompts/compiled`),
    enabled: !!tenantId,
  });
}

export function useActiveCompiledPrompt(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["active-compiled-prompt", tenantId],
    queryFn: () => api.get<CompiledPromptProgram | null>(`/v1/tenants/${tenantId}/prompts/compiled/active`),
    enabled: !!tenantId,
  });
}

export function useCompilePrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCompilationRequest) =>
      api.post<PromptCompilationResult>(`/v1/tenants/${tenantId}/prompts/compile`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compiled-prompts", tenantId] });
      qc.invalidateQueries({ queryKey: ["active-compiled-prompt", tenantId] });
    },
  });
}

export function useActivateCompiledPrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) =>
      api.post<CompiledPromptProgram>(`/v1/tenants/${tenantId}/prompts/compiled/${encodeURIComponent(programId)}/activate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compiled-prompts", tenantId] });
      qc.invalidateQueries({ queryKey: ["active-compiled-prompt", tenantId] });
    },
  });
}

export function useDeactivateCompiledPrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) =>
      api.post<CompiledPromptProgram>(`/v1/tenants/${tenantId}/prompts/compiled/${encodeURIComponent(programId)}/deactivate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compiled-prompts", tenantId] });
      qc.invalidateQueries({ queryKey: ["active-compiled-prompt", tenantId] });
    },
  });
}

export function useDeleteCompiledPrompt(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (programId: string) =>
      api.delete<{ success: boolean; program_id: string }>(`/v1/tenants/${tenantId}/prompts/compiled/${encodeURIComponent(programId)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compiled-prompts", tenantId] });
      qc.invalidateQueries({ queryKey: ["active-compiled-prompt", tenantId] });
    },
  });
}

