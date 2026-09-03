import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type RegionCode = "ap-south" | "us-east" | "eu-central" | "auto";
export type ReplicaHealthStatus = "healthy" | "degraded" | "unreachable" | "fallback_primary";

export interface RegionNodeConfig {
  region_code: RegionCode;
  region_name: string;
  city: string;
  is_primary: boolean;
  is_configured: boolean;
  endpoint_display: string;
  status: ReplicaHealthStatus;
  latency_ms: number | null;
  last_probe_at: string | null;
}

export interface EdgeRoutingDecision {
  client_country: string;
  detected_continent: string;
  selected_region: RegionCode;
  target_endpoint: string;
  is_fallback: boolean;
  estimated_primary_latency_ms: number;
  estimated_replica_latency_ms: number;
  estimated_reduction_pct: number;
  routing_reason: string;
}

export interface MultiRegionClusterStatus {
  primary_region: RegionCode;
  total_regions: number;
  configured_replicas: number;
  active_routing_mode: string;
  regions: RegionNodeConfig[];
  timestamp: string;
}

export interface RegionProbeResult {
  region_code: RegionCode;
  status: ReplicaHealthStatus;
  latency_ms: number;
  probed_at: string;
}

export interface RegionProbeResponse {
  probed_at: string;
  results: RegionProbeResult[];
  overall_health: string;
}

function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("retriever_admin_key") || "dev-admin-master-key-change-in-production";
}

export function useClusterRegions() {
  return useQuery<MultiRegionClusterStatus>({
    queryKey: ["admin", "regions"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/v1/admin/platform/regions`, {
        headers: {
          "X-Admin-Key": getAdminKey(),
        },
      });
      if (!res.ok) {
        throw new Error("Failed to load multi-region cluster status");
      }
      return res.json();
    },
    refetchInterval: 30000,
  });
}

export function useProbeRegions() {
  const queryClient = useQueryClient();
  return useMutation<RegionProbeResponse, Error>({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/v1/admin/platform/regions/probe`, {
        method: "POST",
        headers: {
          "X-Admin-Key": getAdminKey(),
        },
      });
      if (!res.ok) {
        throw new Error("Regional probe failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "regions"] });
    },
  });
}

export function usePreviewRouting() {
  return useMutation<EdgeRoutingDecision, Error, string>({
    mutationFn: async (country: string) => {
      const res = await fetch(
        `${API_BASE}/v1/admin/platform/regions/preview?country=${encodeURIComponent(country)}`,
        {
          headers: {
            "X-Admin-Key": getAdminKey(),
          },
        }
      );
      if (!res.ok) {
        throw new Error("Routing preview failed");
      }
      return res.json();
    },
  });
}
