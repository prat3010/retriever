import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ProjectedPoint {
  chunk_id: string;
  document_id: string;
  document_title: string;
  coordinates: number[];
  cluster_id: number;
  cluster_label: string;
  text_preview: string;
  metadata?: Record<string, unknown>;
}

export interface ProjectionCentroid {
  cluster_id: number;
  label: string;
  coordinates: number[];
  chunk_count: number;
}

export interface EmbeddingProjectionRequest {
  method?: "pca" | "tsne" | "umap";
  dimensions?: number;
  perplexity?: number;
  n_neighbors?: number;
  min_dist?: number;
  normalize?: boolean;
  query_vector?: number[];
  query_text?: string;
}

export interface EmbeddingProjectionResponse {
  tenant_id: string;
  total_points: number;
  dimensions: number;
  method_used: string;
  points: ProjectedPoint[];
  centroids: ProjectionCentroid[];
  variance_explained: number[] | null;
  silhouette_score: number | null;
  query_point: ProjectedPoint | null;
}

export function useTenantProjections(
  tenantId: string | undefined,
  requestParams: EmbeddingProjectionRequest = { method: "pca", dimensions: 2, normalize: true }
) {
  return useQuery({
    queryKey: ["tenant-projections", tenantId, requestParams],
    queryFn: () =>
      api.post<EmbeddingProjectionResponse>(
        `/v1/tenants/${tenantId}/embeddings/project`,
        requestParams
      ),
    enabled: !!tenantId,
  });
}

export function useProjectEmbeddingsMutation(tenantId: string | undefined) {
  return useMutation({
    mutationFn: (req: EmbeddingProjectionRequest) =>
      api.post<EmbeddingProjectionResponse>(
        `/v1/tenants/${tenantId}/embeddings/project`,
        req
      ),
  });
}
