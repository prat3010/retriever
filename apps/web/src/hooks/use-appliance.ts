import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface ApplianceHardwareAttestation {
  platform: string;
  hardware_root: string;
  pcr_measurement: string;
  key_id: string;
  sealed_at: string;
  signature: string;
}

export interface AirgapNetworkAudit {
  audited_at: string;
  active_interfaces: string[];
  active_sockets_count: number;
  dns_resolvers: string[];
  blocked_egress_attempts: number;
  is_compliant: boolean;
  audit_notes: string;
}

export interface SealedVectorStoreMetadata {
  tenant_id: string;
  database_file: string;
  chunk_count: number;
  vector_dimension: number;
  sealing_state: "unsealed" | "sealed" | "locked_tamper_detected" | "provisioning";
  cipher_suite: string;
  sealed_checksum_sha256: string;
  hardware_fingerprint: string;
}

export interface EmbeddedModelManifestItem {
  model_name: string;
  model_type: string;
  quantization: string;
  file_size_bytes: number;
  sha256_checksum: string;
  is_loaded: boolean;
}

export interface ApplianceStatusDTO {
  appliance_id: string;
  version: string;
  deployment_mode: string;
  sealing_state: "unsealed" | "sealed" | "locked_tamper_detected" | "provisioning";
  network_state: "isolated_compliant" | "egress_violation_detected" | "audit_pending";
  hardware_attestation?: ApplianceHardwareAttestation;
  network_audit?: AirgapNetworkAudit;
  sealed_vector_stores: SealedVectorStoreMetadata[];
  embedded_models: EmbeddedModelManifestItem[];
  uptime_seconds: number;
}

export interface VoiceRAGQueryRequest {
  tenant_id: string;
  audio_bytes_base64: string;
  sample_rate_hz?: number;
  top_k?: number;
  timbre?: string;
  system_prompt?: string;
}

export interface VoiceRAGQueryResponse {
  session_id: string;
  tenant_id: string;
  transcribed_text: string;
  answer_text: string;
  citations: Array<{
    chunk_id?: string;
    document_id?: string;
    content: string;
    score: number;
  }>;
  audio_bytes_base64: string;
  audio_format: string;
  audio_duration_ms: number;
  asr_latency_ms: number;
  retrieval_latency_ms: number;
  synthesis_latency_ms: number;
  tts_latency_ms: number;
  total_latency_ms: number;
}

export function useApplianceStatus() {
  return useQuery<ApplianceStatusDTO>({
    queryKey: ["appliance-status"],
    queryFn: () => api.get<ApplianceStatusDTO>("/v1/appliance/status"),
    refetchInterval: 10000,
  });
}

export function useApplianceManifest() {
  return useQuery<Record<string, unknown>>({
    queryKey: ["appliance-manifest"],
    queryFn: () => api.get<Record<string, unknown>>("/v1/appliance/manifest"),
  });
}

export function useAuditNetwork() {
  const queryClient = useQueryClient();
  return useMutation<AirgapNetworkAudit, Error, { strict_enforce?: boolean }>({
    mutationFn: (vars) =>
      api.post<AirgapNetworkAudit>("/v1/appliance/network/audit", {
        strict_enforce: vars.strict_enforce ?? false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appliance-status"] });
    },
  });
}

export function useSealVectorStore(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    SealedVectorStoreMetadata,
    Error,
    { plain_db_path: string; sealed_db_path: string; chunk_count?: number; vector_dim?: number }
  >({
    mutationFn: (vars) =>
      api.post<SealedVectorStoreMetadata>(`/v1/appliance/tenants/${tenantId}/seal`, vars),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appliance-status"] });
    },
  });
}

export function useUnsealVectorStore(tenantId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    { status: string; success: boolean },
    Error,
    { sealed_db_path: string; unsealed_db_path: string }
  >({
    mutationFn: (vars) =>
      api.post<{ status: string; success: boolean }>(`/v1/appliance/tenants/${tenantId}/unseal`, vars),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appliance-status"] });
    },
  });
}

export function useVoiceRAGQuery(tenantId: string) {
  return useMutation<VoiceRAGQueryResponse, Error, VoiceRAGQueryRequest>({
    mutationFn: (vars) =>
      api.post<VoiceRAGQueryResponse>(`/v1/appliance/tenants/${tenantId}/voice/query`, vars),
  });
}
