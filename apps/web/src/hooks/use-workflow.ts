import { api } from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";

export interface ConfigureWebhookResponse {
  status: string;
  tenant_id: string;
  n8n_webhook_url: string;
  ping_result: {
    success: boolean;
    status_code?: number;
    error?: string;
  };
}

export function useConfigureN8nWebhook(tenantId: string) {
  return useMutation<ConfigureWebhookResponse, Error, string>({
    mutationFn: (n8n_webhook_url: string) =>
      api.post<ConfigureWebhookResponse>(`/v1/admin/tenants/${tenantId}/workflow/webhooks`, { n8n_webhook_url }),
  });
}

export function useN8nSpec() {
  return useQuery<Record<string, unknown>>({
    queryKey: ["n8n-spec"],
    queryFn: () => api.get<Record<string, unknown>>("/v1/workflow/n8n-spec"),
  });
}
