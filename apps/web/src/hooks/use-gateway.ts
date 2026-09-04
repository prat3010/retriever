import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface GatewayModelInfo {
  model_id: string;
  provider: string;
  name: string;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  capabilities: string[];
  is_local: boolean;
  health_status: "healthy" | "degraded" | "unavailable";
  latency_ms?: number | null;
  description: string;
}

export interface GatewayProbeResult {
  provider: string;
  target_model: string;
  reachable: boolean;
  latency_ms: number;
  error_message?: string | null;
}

export interface GatewayRoutesConfig {
  primary_model: string;
  fallback_models: string[];
  latency_sla_ms: number;
  cooldown_seconds: number;
}

export interface BudgetSettingsConfig {
  daily_cost_budget: number | null;
  monthly_cost_budget: number | null;
  hard_limit_action: "warn_only" | "block" | "downgrade_free_model";
  free_fallback_model: string;
  currency: string;
}

export interface TenantGatewayRoutesResponse {
  tenant_id: string;
  gateway_settings: GatewayRoutesConfig;
  budget_settings: BudgetSettingsConfig;
}

export interface VirtualTenantBudget {
  daily_budget: number | null;
  monthly_budget: number | null;
  hard_limit_action: "warn_only" | "block" | "downgrade_free_model";
  free_fallback_model: string;
  currency: string;
  current_daily_spend: number;
  current_monthly_spend: number;
  is_budget_exceeded: boolean;
  cost_by_model: Record<string, number>;
}

export function useGatewayModels() {
  return useQuery({
    queryKey: ["gateway", "models"],
    queryFn: () => api.get<GatewayModelInfo[]>("/v1/gateway/models"),
  });
}

export function useGatewayProbe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<GatewayProbeResult[]>("/v1/gateway/probe", {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["gateway", "models"] });
    },
  });
}

export function useTenantGatewayRoutes(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["gateway", "routes", tenantId],
    queryFn: () => api.get<TenantGatewayRoutesResponse>(`/v1/tenants/${tenantId}/gateway/routes`),
    enabled: !!tenantId,
  });
}

export function useUpdateTenantGatewayRoutes(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      primary_model: string;
      fallback_models: string[];
      latency_sla_ms: number;
      cooldown_seconds: number;
      daily_cost_budget: number | null;
      monthly_cost_budget: number | null;
      hard_limit_action: string;
      free_fallback_model: string;
      currency: string;
    }) => api.put(`/v1/tenants/${tenantId}/gateway/routes`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["gateway", "routes", tenantId] });
      qc.invalidateQueries({ queryKey: ["gateway", "budget", tenantId] });
    },
  });
}

export function useTenantGatewayBudget(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["gateway", "budget", tenantId],
    queryFn: () => api.get<VirtualTenantBudget>(`/v1/tenants/${tenantId}/gateway/budget`),
    enabled: !!tenantId,
  });
}
