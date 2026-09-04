import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PluginItem {
  id: string;
  name: string;
  category: string;
  status: "configured" | "available" | "syncing";
  slash_command?: string;
  webhook_url?: string;
  download_url?: string;
  description: string;
}

export interface IntegrationsOverviewResponse {
  plugins: PluginItem[];
}

export interface ConnectorItem {
  id: string;
  name: string;
  connector_type: "google_drive" | "notion" | "web_crawler" | "slack" | "cloud_drive";
  status: "idle" | "syncing" | "failed" | "disabled";
  sync_interval_minutes: number;
  configuration: Record<string, any>;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
}

function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("retriever_admin_key") || "dev-admin-master-key-change-in-production";
}

export function useIntegrationsOverview() {
  return useQuery<IntegrationsOverviewResponse>({
    queryKey: ["integrations", "overview"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/integrations/overview`, {
        headers: {
          "X-Admin-Key": getAdminKey(),
        },
      });
      if (!res.ok) {
        throw new Error("Failed to fetch integrations overview");
      }
      return res.json();
    },
    staleTime: 30_000,
  });
}

export function useTenantConnectors(tenantId: string) {
  return useQuery<ConnectorItem[]>({
    queryKey: ["connectors", tenantId],
    queryFn: async () => {
      if (!tenantId) return [];
      const res = await fetch(`${API_BASE}/v1/admin/tenants/${tenantId}/connectors`, {
        headers: {
          "X-Admin-Key": getAdminKey(),
        },
      });
      if (!res.ok) {
        if (res.status === 404) return [];
        throw new Error("Failed to fetch tenant connectors");
      }
      return res.json();
    },
    enabled: Boolean(tenantId),
    staleTime: 10_000,
  });
}

export function useTriggerConnectorSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ tenantId, connectorId }: { tenantId: string; connectorId: string }) => {
      const res = await fetch(
        `${API_BASE}/v1/admin/tenants/${tenantId}/connectors/${connectorId}/sync`,
        {
          method: "POST",
          headers: {
            "X-Admin-Key": getAdminKey(),
          },
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Sync failed");
      }
      return res.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["connectors", variables.tenantId] });
      queryClient.invalidateQueries({ queryKey: ["integrations", "overview"] });
    },
  });
}

export function useCreateConnector() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      tenantId,
      name,
      connectorType,
      configuration,
    }: {
      tenantId: string;
      name: string;
      connectorType: string;
      configuration: Record<string, any>;
    }) => {
      const res = await fetch(`${API_BASE}/v1/admin/tenants/${tenantId}/connectors`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Key": getAdminKey(),
        },
        body: JSON.stringify({
          name,
          connector_type: connectorType,
          configuration,
          sync_interval_minutes: 1440,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to create connector");
      }
      return res.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["connectors", variables.tenantId] });
    },
  });
}
