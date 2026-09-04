import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type GuardrailExecutionMode =
  | "disabled"
  | "input_only"
  | "output_grounding_only"
  | "full_conversational";

export interface ColangFlowDefinition {
  name: string;
  user_intent: string;
  bot_response: string;
  priority: number;
}

export interface GuardrailRule {
  rule_id: string;
  name: string;
  category: string;
  enabled: boolean;
  threshold?: number;
}

export interface TenantGuardrailsConfig {
  tenant_id: string;
  mode: GuardrailExecutionMode;
  colang_script: string;
  active_flows: ColangFlowDefinition[];
  rules: GuardrailRule[];
  pii_redaction_enabled: boolean;
  competitor_shield_enabled: boolean;
  competitor_names: string[];
  brand_tone: string;
  grounding_threshold: number;
  fallback_response: string;
  updated_at: string;
}

export interface GuardrailViolation {
  rule_id: string;
  rail_type: string;
  action_taken: "block" | "steer" | "warn" | "log";
  reason: string;
  matched_pattern?: string | null;
  latency_ms: number;
  timestamp: string;
}

export interface GuardrailCheckResult {
  passed: boolean;
  action: "allow" | "block" | "steer";
  violations: GuardrailViolation[];
  steered_response?: string | null;
  fast_path_matched: boolean;
  latency_ms: number;
}

export interface GuardrailTemplate {
  name: string;
  description: string;
  colang: string;
  rules: Array<{
    rule_id: string;
    name: string;
    category: string;
    enabled: boolean;
  }>;
}

export interface GuardrailsOverviewResponse {
  engine: string;
  version: string;
  battery_status: string;
  supported_modes: string[];
  fast_path_latency: string;
  grounding_latency: string;
}

export interface GuardrailsTelemetryResponse {
  tenant_id: string;
  total_violations: number;
  total_blocked: number;
  total_steered: number;
  recent_violations: GuardrailViolation[];
  average_rail_latency_ms: number;
}

export interface UpdateGuardrailsPayload {
  mode?: GuardrailExecutionMode;
  colang_script?: string;
  pii_redaction_enabled?: boolean;
  competitor_shield_enabled?: boolean;
  competitor_names?: string[];
  brand_tone?: string;
  grounding_threshold?: number;
  fallback_response?: string;
}

export interface ValidateInputPayload {
  query: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface ValidateOutputPayload {
  query: string;
  generated_response: string;
  retrieved_contexts: string[];
}

export interface TestFlowPayload {
  query: string;
  custom_colang?: string;
}

export function useGuardrailsOverview() {
  return useQuery({
    queryKey: ["guardrails", "overview"],
    queryFn: () => api.get<GuardrailsOverviewResponse>("/v1/guardrails/overview"),
  });
}

export function useGuardrailTemplates() {
  return useQuery({
    queryKey: ["guardrails", "templates"],
    queryFn: () => api.get<Record<string, GuardrailTemplate>>("/v1/guardrails/templates"),
  });
}

export function useTenantGuardrailsConfig(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["guardrails-config", tenantId],
    queryFn: () => api.get<TenantGuardrailsConfig>(`/v1/tenants/${tenantId}/guardrails/config`),
    enabled: !!tenantId,
  });
}

export function useUpdateTenantGuardrailsConfig(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateGuardrailsPayload) =>
      api.put<TenantGuardrailsConfig>(`/v1/tenants/${tenantId}/guardrails/config`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["guardrails-config", tenantId] });
      qc.invalidateQueries({ queryKey: ["guardrails-telemetry", tenantId] });
    },
  });
}

export function useValidateGuardrailsInput(tenantId: string) {
  return useMutation({
    mutationFn: (payload: ValidateInputPayload) =>
      api.post<GuardrailCheckResult>(`/v1/tenants/${tenantId}/guardrails/validate-input`, payload),
  });
}

export function useValidateGuardrailsOutput(tenantId: string) {
  return useMutation({
    mutationFn: (payload: ValidateOutputPayload) =>
      api.post<GuardrailCheckResult>(`/v1/tenants/${tenantId}/guardrails/validate-output`, payload),
  });
}

export function useTestGuardrailFlow(tenantId: string) {
  return useMutation({
    mutationFn: (payload: TestFlowPayload) =>
      api.post<GuardrailCheckResult>(`/v1/tenants/${tenantId}/guardrails/test-flow`, payload),
  });
}

export function useGuardrailsTelemetry(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["guardrails-telemetry", tenantId],
    queryFn: () => api.get<GuardrailsTelemetryResponse>(`/v1/tenants/${tenantId}/guardrails/telemetry`),
    enabled: !!tenantId,
    refetchInterval: 10000,
  });
}
