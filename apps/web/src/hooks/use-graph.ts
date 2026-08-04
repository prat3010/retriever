import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface GraphCapabilities {
  machine_profile: string;
  supported_engines: string[];
  active_engine: string;
  neo4j_status: string;
  message: string;
}

export interface GraphSummary {
  tenant_id: string;
  total_triples: number;
  unique_entities: number;
  storage_engine: string;
  neo4j_status?: string | null;
}

export interface GraphTriple {
  triple_id?: string | null;
  subject: string;
  predicate: string;
  object: string;
  chunk_id?: string | null;
  confidence: number;
}

export interface GraphQueryResult {
  root_entity: string;
  max_hops: number;
  triples: GraphTriple[];
  connected_entities: string[];
}

interface GraphStatus {
  capabilities: GraphCapabilities;
  summary: GraphSummary;
}

export function useGraphStatus(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["graph-status", tenantId],
    queryFn: async () => {
      const [capabilities, summary] = await Promise.all([
        api.get<GraphCapabilities>(`/v1/admin/tenants/${tenantId}/graph/capabilities`),
        api.get<GraphSummary>(`/v1/admin/tenants/${tenantId}/graph`),
      ]);
      return { capabilities, summary } satisfies GraphStatus;
    },
    enabled: !!tenantId,
  });
}

export function useSwitchGraphEngine(tenantId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (engine: "postgres" | "neo4j") => {
      await api.post(`/v1/admin/tenants/${tenantId}/graph/engine`, { engine });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graph-status", tenantId] });
    },
  });
}

export function useGraphQuery(tenantId: string | undefined) {
  return useMutation({
    mutationFn: async ({ entity, maxHops }: { entity: string; maxHops: number }) => {
      return api.post<GraphQueryResult>(`/v1/admin/tenants/${tenantId}/graph/query`, {
        entity,
        max_hops: maxHops,
      });
    },
  });
}

export function useDeleteGraphTriple(tenantId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tripleId: string) => {
      await api.delete(`/v1/admin/tenants/${tenantId}/graph/triples/${tripleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["graph-status", tenantId] });
    },
  });
}
