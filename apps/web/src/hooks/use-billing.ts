import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface PaymentTransaction {
  transaction_id: string;
  tenant_id: string;
  provider: string;
  event_type: string;
  amount: number;
  currency: string;
  status: string;
  external_reference: string;
  created_at: string;
}

export interface PaymentLedgerResponse {
  tenant_id: string;
  total_transactions: number;
  transactions: PaymentTransaction[];
}

export interface CreateCheckoutRequest {
  tenant_id: string;
  plan_id: string;
  provider: string;
  amount: number;
  currency: string;
}

export interface CreateCheckoutResponse {
  checkout_url: string;
  session_id: string;
  provider: string;
}

export function usePaymentLedger(tenantId: string) {
  return useQuery<PaymentLedgerResponse>({
    queryKey: ["payments", tenantId],
    queryFn: () => api.get<PaymentLedgerResponse>(`/v1/admin/tenants/${tenantId}/payments/ledger`),
    enabled: !!tenantId,
  });
}

export function useCreateCheckoutSession() {
  const queryClient = useQueryClient();
  return useMutation<CreateCheckoutResponse, Error, CreateCheckoutRequest>({
    mutationFn: (payload: CreateCheckoutRequest) =>
      api.post<CreateCheckoutResponse>("/v1/payments/checkout-session", payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["payments", variables.tenant_id] });
    },
  });
}
