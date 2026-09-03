import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export type PiiCategory = "financial" | "identification" | "secrets" | "network" | "health_hipaa" | "contact";
export type MaskingMode = "redact" | "synthetic" | "pseudonymize";

export interface PiiEntityMatch {
  category: PiiCategory;
  entity_type: string;
  original_value: string;
  masked_value: string;
  start: number;
  end: number;
}

export interface AnonymizeTestRequest {
  text: string;
  categories?: PiiCategory[];
  masking_mode?: MaskingMode;
  custom_patterns?: string[];
}

export interface AnonymizeTestResponse {
  redacted_text: string;
  original_length: number;
  total_redacted: number;
  entities_detected: PiiEntityMatch[];
}

export interface ComplianceCertificateDTO {
  certificate_id: string;
  tenant_id: string;
  requester: string;
  reason: string;
  timestamp: string;
  erasure_scope: "document" | "full_tenant_wipe";
  target_id?: string | null;
  records_purged: Record<string, number>;
  sha256_audit_signature: string;
  verification_status: string;
}

export interface PurgeTenantResponse {
  status: string;
  tenantId: string;
  stats: Record<string, number>;
  certificate?: ComplianceCertificateDTO;
}

export interface VerificationResponse {
  certificate_id: string;
  is_valid: boolean;
  audit_signature: string;
  certificate?: ComplianceCertificateDTO | null;
  message: string;
}

export function useAnonymizeTest(tenantId: string) {
  return useMutation<AnonymizeTestResponse, Error, AnonymizeTestRequest>({
    mutationFn: (payload: AnonymizeTestRequest) =>
      api.post<AnonymizeTestResponse>(`/v1/admin/tenants/${tenantId}/compliance/anonymize`, payload),
  });
}

export function useComplianceCertificates(tenantId: string) {
  return useQuery<ComplianceCertificateDTO[], Error>({
    queryKey: ["compliance-certificates", tenantId],
    queryFn: () =>
      api.get<ComplianceCertificateDTO[]>(`/v1/admin/tenants/${tenantId}/compliance/certificates`),
    enabled: Boolean(tenantId),
  });
}

export function useVerifyCertificate() {
  return useMutation<VerificationResponse, Error, string>({
    mutationFn: (certificateId: string) =>
      api.get<VerificationResponse>(`/v1/admin/compliance/verify/${certificateId}`),
  });
}

export function usePurgeTenantData(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<PurgeTenantResponse, Error, void>({
    mutationFn: () =>
      api.post<PurgeTenantResponse>(`/v1/admin/tenants/${tenantId}/compliance/forget`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["tenants", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["compliance-certificates", tenantId] });
    },
  });
}

export function useRunRetentionPurge(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<{ status: string; result: { scanned: number; purged: number } }, Error, void>({
    mutationFn: () =>
      api.post<{ status: string; result: { scanned: number; purged: number } }>(
        `/v1/admin/tenants/${tenantId}/compliance/run-retention-purge`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
    },
  });
}
