"""Embedding Space Projection Adapter using Scikit-Learn (PCA, t-SNE) & UMAP.

Converts high-dimensional (768-dim) chunk embeddings and live search query vectors
into normalized 2D/3D Cartesian coordinates with cluster centroid aggregations and
silhouette separation metrics for SaaS Studio 3D visualization.
"""

import logging
from collections import defaultdict
from typing import Any

import numpy as np

from src.domain.projection.abstractions import (
    BaseEmbeddingProjector,
    EmbeddingProjectionRequest,
    EmbeddingProjectionResponse,
    ProjectedPoint,
    ProjectionCentroid,
)

logger = logging.getLogger(__name__)


class EmbeddingProjectionAdapter(BaseEmbeddingProjector):
    """Scikit-Learn & UMAP Multi-Algorithm Dimensionality Reduction Engine."""

    def __init__(self):
        self._umap_available = False
        try:
            import umap  # noqa: F401

            self._umap_available = True
        except ImportError:
            logger.info("UMAP package not found; PCA and t-SNE will be used as standard engines.")

    def project_embeddings(
        self,
        tenant_id: str,
        chunk_ids: list[str],
        chunk_texts: list[str],
        document_ids: list[str],
        document_titles: list[str],
        embeddings: list[list[float]],
        cluster_ids: list[int] | None = None,
        cluster_labels: dict[int, str] | None = None,
        request: EmbeddingProjectionRequest | None = None,
    ) -> EmbeddingProjectionResponse:
        """Project high-dimensional embeddings down to 2D/3D coordinates."""
        req = request or EmbeddingProjectionRequest()
        total_points = len(chunk_ids)

        if total_points == 0 or len(embeddings) == 0:
            return EmbeddingProjectionResponse(
                tenant_id=tenant_id,
                total_points=0,
                dimensions=req.dimensions,
                method_used="none",
                points=[],
                centroids=[],
                variance_explained=None,
                silhouette_score=None,
                query_point=None,
            )

        embeddings_matrix = np.array(embeddings, dtype=np.float32)
        n_samples, n_features = embeddings_matrix.shape
        target_dims = min(req.dimensions, n_features)

        # Default cluster assignments if not provided
        if cluster_ids is None or len(cluster_ids) != total_points:
            cluster_ids = [0] * total_points
        if cluster_labels is None:
            cluster_labels = {0: "General Knowledge"}

        # Handle very small collections (< 3 chunks) directly
        if n_samples < 3:
            coords_3d = self._project_minimal_samples(embeddings_matrix, target_dims)
            algo_used = "direct_identity"
            variance_explained = [1.0] * target_dims
        else:
            coords_3d, algo_used, variance_explained, fitted_model = self._fit_transform(
                embeddings_matrix, req, target_dims
            )

        # Normalize coordinates into [-100, 100] bounding space
        if req.normalize and n_samples > 1:
            coords_3d = self._normalize_coordinates(coords_3d)

        # Build ProjectedPoint instances
        points: list[ProjectedPoint] = []
        cluster_points_map = defaultdict(list)

        for i in range(total_points):
            cid = cluster_ids[i] if i < len(cluster_ids) else 0
            label = cluster_labels.get(cid, f"Topic {cid}" if cid != -1 else "Miscellaneous / Outliers")
            coord_list = [round(float(c), 4) for c in coords_3d[i]]
            preview = (chunk_texts[i][:180] + "...") if len(chunk_texts[i]) > 180 else chunk_texts[i]

            pt = ProjectedPoint(
                chunk_id=chunk_ids[i],
                document_id=document_ids[i] if i < len(document_ids) else "",
                document_title=document_titles[i] if i < len(document_titles) else "Document",
                coordinates=coord_list,
                cluster_id=cid,
                cluster_label=label,
                text_preview=preview,
                metadata={"original_dim": n_features},
            )
            points.append(pt)
            cluster_points_map[cid].append(coords_3d[i])

        # Compute cluster centroids
        centroids: list[ProjectionCentroid] = []
        for cid, coord_arr_list in cluster_points_map.items():
            if cid == -1:
                continue  # Skip outliers for centroids
            arr = np.array(coord_arr_list)
            centroid_coords = np.mean(arr, axis=0)
            centroids.append(
                ProjectionCentroid(
                    cluster_id=cid,
                    cluster_label=cluster_labels.get(cid, f"Topic {cid}"),
                    coordinates=[round(float(c), 4) for c in centroid_coords],
                    chunk_count=len(coord_arr_list),
                )
            )
        centroids.sort(key=lambda c: c.chunk_count, reverse=True)

        # Compute silhouette quality score if applicable
        silhouette_score = self._compute_silhouette(embeddings_matrix, cluster_ids)

        # Project dynamic query vector if provided
        query_point = None
        if req.query_vector and len(req.query_vector) == n_features:
            query_point = self._project_query(
                req.query_vector,
                embeddings_matrix,
                coords_3d,
                algo_used,
                fitted_model if "fitted_model" in locals() else None,
                target_dims,
                req.normalize,
            )

        return EmbeddingProjectionResponse(
            tenant_id=tenant_id,
            total_points=total_points,
            dimensions=target_dims,
            method_used=algo_used,
            points=points,
            centroids=centroids,
            variance_explained=variance_explained,
            silhouette_score=silhouette_score,
            query_point=query_point,
        )

    def _fit_transform(self, X: np.ndarray, req: EmbeddingProjectionRequest, dims: int):
        """Fit and transform embeddings using requested method."""
        method = req.method.lower().strip()
        n_samples = X.shape[0]

        if method == "umap" and self._umap_available and n_samples >= 5:
            try:
                import umap

                n_neighbors = max(2, min(req.n_neighbors, n_samples - 1))
                model = umap.UMAP(
                    n_neighbors=n_neighbors,
                    min_dist=req.min_dist,
                    n_components=dims,
                    random_state=42,
                )
                coords = model.fit_transform(X)
                return coords, "umap", None, model
            except Exception as e:
                logger.warning("UMAP failed (%s); falling back to PCA.", e)

        if method == "tsne" and n_samples >= 4:
            try:
                from sklearn.manifold import TSNE

                # t-SNE perplexity must be strictly less than n_samples
                safe_perplexity = max(1.0, min(req.perplexity, (n_samples - 1) / 3.0))
                model = TSNE(
                    n_components=dims,
                    perplexity=safe_perplexity,
                    random_state=42,
                    init="pca",
                    learning_rate="auto",
                )
                coords = model.fit_transform(X)
                return coords, "tsne", None, model
            except Exception as e:
                logger.warning("t-SNE failed (%s); falling back to PCA.", e)

        # Default fast deterministic PCA with pure NumPy SVD fallback
        pca_dims = min(dims, n_samples, X.shape[1])
        try:
            from sklearn.decomposition import PCA

            model = PCA(n_components=pca_dims, random_state=42)
            coords = model.fit_transform(X)
            var_explained = [round(float(v), 4) for v in model.explained_variance_ratio_]
        except Exception:
            mean = np.mean(X, axis=0)
            x_centered = X - mean
            _, s_vals, vt_mat = np.linalg.svd(x_centered, full_matrices=False)
            coords = np.dot(x_centered, vt_mat[:pca_dims].T)
            total_variance = np.sum(s_vals**2)
            var_explained = (
                [round(float((s**2) / total_variance), 4) for s in s_vals[:pca_dims]]
                if total_variance > 1e-9
                else [0.0] * pca_dims
            )
            model = None


        # Pad with zeros if pca_dims < dims
        if coords.shape[1] < dims:
            padding = np.zeros((n_samples, dims - coords.shape[1]), dtype=np.float32)
            coords = np.hstack([coords, padding])

        return coords, "pca", var_explained, model


    def _normalize_coordinates(self, coords: np.ndarray, target_range: float = 90.0) -> np.ndarray:
        """Center and scale coordinates to [-target_range, target_range]."""
        centered = coords - np.mean(coords, axis=0)
        max_dist = np.max(np.abs(centered))
        if max_dist > 1e-7:
            scaled = (centered / max_dist) * target_range
            return scaled
        return centered

    def _project_minimal_samples(self, X: np.ndarray, dims: int) -> np.ndarray:
        """Handle 1 or 2 sample edge cases with deterministic projection."""
        n_samples = X.shape[0]
        if n_samples == 1:
            return np.zeros((1, dims), dtype=np.float32)
        if n_samples == 2:
            # Place two points symmetrically along the x-axis
            res = np.zeros((2, dims), dtype=np.float32)
            res[0, 0] = -50.0
            res[1, 0] = 50.0
            return res
        return np.zeros((n_samples, dims), dtype=np.float32)

    def _compute_silhouette(self, X: np.ndarray, labels: list[int]) -> float | None:
        """Compute Silhouette coefficient for cluster validation."""
        unique_labels = set(labels) - {-1}
        if len(unique_labels) < 2 or X.shape[0] < 4:
            return None
        try:
            from sklearn.metrics import silhouette_score

            score = float(silhouette_score(X, labels))
            return round(score, 4)
        except Exception:
            return None

    def _project_query(
        self,
        query_vec: list[float],
        X: np.ndarray,
        coords_3d: np.ndarray,
        algo: str,
        model: Any,
        dims: int,
        normalize: bool,
    ) -> ProjectedPoint:
        """Project live query vector into the 2D/3D coordinate manifold."""
        q_arr = np.array([query_vec], dtype=np.float32)

        if algo == "pca" and model is not None and hasattr(model, "transform"):
            try:
                q_coords = model.transform(q_arr)
                if q_coords.shape[1] < dims:
                    padding = np.zeros((1, dims - q_coords.shape[1]), dtype=np.float32)
                    q_coords = np.hstack([q_coords, padding])
                if normalize and X.shape[0] > 1:
                    centered = q_coords - np.mean(coords_3d, axis=0)
                    max_dist = np.max(np.abs(coords_3d)) + 1e-7
                    q_coords = (centered / max_dist) * 90.0
                return ProjectedPoint(
                    chunk_id="query_vector",
                    document_title="Search Query",
                    coordinates=[round(float(c), 4) for c in q_coords[0]],
                    cluster_id=-2,
                    cluster_label="Active Search Vector",
                    text_preview="Current active search query embedding vector",
                )
            except Exception as e:
                logger.debug("PCA query transform fallback: %s", e)

        # For non-linear manifolds (t-SNE/UMAP) or fallback, use distance-weighted kNN projection
        # Compute cosine similarity between query and all chunk vectors
        norm_q = q_arr / (np.linalg.norm(q_arr) + 1e-9)
        norm_x = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        sims = np.dot(norm_x, norm_q.T).flatten()  # Shape: (n_samples,)

        # Take top-5 nearest neighbors
        k = min(5, len(sims))
        top_k_indices = np.argsort(sims)[-k:]
        weights = np.maximum(0.01, sims[top_k_indices])
        weights /= np.sum(weights)

        interpolated_coords = np.sum(coords_3d[top_k_indices] * weights[:, np.newaxis], axis=0)

        return ProjectedPoint(
            chunk_id="query_vector",
            document_title="Search Query",
            coordinates=[round(float(c), 4) for c in interpolated_coords],
            cluster_id=-2,
            cluster_label="Active Search Vector",
            text_preview="Projected search query vector via kNN manifold interpolation",
        )
