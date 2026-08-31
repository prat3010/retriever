"""Topic Clustering Adapter using Scikit-Learn HDBSCAN & c-TF-IDF.

Provides unsupervised clustering of document chunk embeddings, automatic
semantic topic labeling, and knowledge gap detection for GraphRAG and vault analytics.
"""

import logging
from collections import defaultdict

import numpy as np

from src.domain.clustering.abstractions import (
    BaseKnowledgeGapDetector,
    BaseTopicClusterer,
    ClusterTopic,
    KnowledgeGapReport,
    TopicClusteringRequest,
    TopicClusteringResponse,
)

logger = logging.getLogger(__name__)


class TopicClusteringAdapter(BaseTopicClusterer, BaseKnowledgeGapDetector):
    """Scikit-Learn based HDBSCAN & c-TF-IDF Topic Modeling Engine."""

    def __init__(self):
        self._hdbscan_available = True
        try:
            from sklearn.cluster import HDBSCAN  # noqa: F401
        except ImportError:
            logger.warning("HDBSCAN not available in scikit-learn; will use KMeans fallback.")
            self._hdbscan_available = False

    def cluster_chunks(
        self,
        tenant_id: str,
        chunk_ids: list[str],
        chunk_texts: list[str],
        embeddings: list[list[float]],
        request: TopicClusteringRequest,
    ) -> TopicClusteringResponse:
        """Execute unsupervised clustering and synthesize c-TF-IDF topic labels."""
        total_chunks = len(chunk_ids)
        if total_chunks == 0 or len(embeddings) == 0:
            return TopicClusteringResponse(
                tenant_id=tenant_id,
                total_chunks=0,
                total_clusters=0,
                topics=[],
                outlier_chunk_count=0,
                algorithm_used="none",
            )

        embeddings_matrix = np.array(embeddings, dtype=np.float32)

        # Handle very small collections (< 4 chunks)
        if total_chunks < 4:
            topic = self._create_single_fallback_topic(0, chunk_ids, chunk_texts, embeddings_matrix)
            return TopicClusteringResponse(
                tenant_id=tenant_id,
                total_chunks=total_chunks,
                total_clusters=1,
                topics=[topic],
                outlier_chunk_count=0,
                algorithm_used="fallback_single",
            )

        labels, algo_name = self._run_clustering(embeddings_matrix, request, total_chunks)

        # Group chunks by cluster label
        cluster_chunks = defaultdict(list)
        cluster_texts = defaultdict(list)
        cluster_vectors = defaultdict(list)

        for cid, text, vec, lbl in zip(chunk_ids, chunk_texts, embeddings_matrix, labels, strict=False):
            cluster_chunks[lbl].append(cid)
            cluster_texts[lbl].append(text)
            cluster_vectors[lbl].append(vec)

        # Compute c-TF-IDF keywords per cluster
        keywords_per_cluster = self._extract_c_tfidf_keywords(
            cluster_texts, request.top_k_keywords
        )

        topics: list[ClusterTopic] = []
        outlier_count = 0

        for lbl, c_ids in sorted(cluster_chunks.items()):
            if lbl == -1:
                # Outlier noise cluster in HDBSCAN
                outlier_count = len(c_ids)
                topics.append(
                    ClusterTopic(
                        topic_id=-1,
                        label="Miscellaneous / Outliers",
                        keywords=keywords_per_cluster.get(-1, ["unclassified", "isolated"]),
                        chunk_ids=c_ids,
                        chunk_count=len(c_ids),
                        centroid=[],
                        coherence_score=0.2,
                        metadata={"is_outlier": True},
                    )
                )
                continue

            vecs = np.array(cluster_vectors[lbl])
            centroid = np.mean(vecs, axis=0)

            # Compute average cosine coherence to centroid
            norm_centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
            norm_vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
            coherence = float(np.mean(np.dot(norm_vecs, norm_centroid)))
            coherence = max(0.0, min(1.0, coherence))

            kw = keywords_per_cluster.get(lbl, ["topic", "cluster"])
            topic_label = " & ".join(kw[:2]).title() if kw else f"Topic {lbl}"

            topics.append(
                ClusterTopic(
                    topic_id=int(lbl),
                    label=topic_label,
                    keywords=kw,
                    chunk_ids=c_ids,
                    chunk_count=len(c_ids),
                    centroid=centroid.tolist(),
                    coherence_score=round(coherence, 4),
                    metadata={"is_outlier": False},
                )
            )

        # Sort topics by chunk count descending (excluding outliers at end)
        regular_topics = [t for t in topics if t.topic_id != -1]
        regular_topics.sort(key=lambda t: t.chunk_count, reverse=True)
        outlier_topics = [t for t in topics if t.topic_id == -1]

        final_topics = regular_topics + outlier_topics

        return TopicClusteringResponse(
            tenant_id=tenant_id,
            total_chunks=total_chunks,
            total_clusters=len(regular_topics),
            topics=final_topics,
            outlier_chunk_count=outlier_count,
            algorithm_used=algo_name,
        )

    def _run_clustering(self, X: np.ndarray, request: TopicClusteringRequest, n_samples: int):
        """Execute HDBSCAN or MiniBatchKMeans."""
        if request.method == "hdbscan" and self._hdbscan_available and n_samples >= 5:
            try:
                from sklearn.cluster import HDBSCAN

                min_size = max(2, min(request.min_cluster_size, n_samples // 2))
                clusterer = HDBSCAN(
                    min_cluster_size=min_size,
                    metric="euclidean",
                    cluster_selection_epsilon=0.1,
                )
                labels = clusterer.fit_predict(X)
                # If HDBSCAN classified everything as noise (-1), fall back to KMeans
                unique_labels = set(labels)
                if unique_labels == {-1} or len(unique_labels) == 1:
                    return self._run_kmeans(X, n_samples)
                return labels, "hdbscan"
            except Exception as e:
                logger.warning(f"HDBSCAN clustering failed: {e}; falling back to KMeans")

        return self._run_kmeans(X, n_samples)

    def _run_kmeans(self, X: np.ndarray, n_samples: int):
        """KMeans clustering using scikit-learn or pure NumPy EM clustering."""
        k = max(2, min(n_samples // 3, 10))
        try:
            from sklearn.cluster import MiniBatchKMeans

            kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, n_init=3)
            labels = kmeans.fit_predict(X)
            return labels, "minibatch_kmeans"
        except ImportError:
            # Pure NumPy cosine KMeans implementation
            return self._numpy_kmeans(X, k), "numpy_kmeans"

    def _numpy_kmeans(self, X: np.ndarray, k: int, max_iter: int = 20) -> list[int]:
        """Pure NumPy K-Means clustering algorithm."""
        n = len(X)
        if n <= k:
            return list(range(n))

        # Initialize centroids randomly
        rng = np.random.RandomState(42)
        indices = rng.choice(n, size=k, replace=False)
        centroids = X[indices].copy()

        labels = np.zeros(n, dtype=int)
        for _ in range(max_iter):
            # Compute squared euclidean distances to all centroids
            dists = np.linalg.norm(X[:, np.newaxis, :] - centroids[np.newaxis, :, :], axis=2)
            new_labels = np.argmin(dists, axis=1)

            if np.array_equal(labels, new_labels):
                break
            labels = new_labels

            # Recompute centroids
            for j in range(k):
                mask = labels == j
                if np.any(mask):
                    centroids[j] = np.mean(X[mask], axis=0)

        return labels.tolist()

    def _extract_c_tfidf_keywords(
        self, cluster_texts: dict[int, list[str]], top_k: int
    ) -> dict[int, list[str]]:
        """Extract top representative keywords per cluster using class-based TF-IDF."""
        cluster_docs = []
        cluster_ids = []

        for lbl, texts in cluster_texts.items():
            cluster_docs.append(" ".join(texts))
            cluster_ids.append(lbl)

        if not cluster_docs:
            return {}

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words="english",
                ngram_range=(1, 2),
                token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
            )
            tfidf_matrix = vectorizer.fit_transform(cluster_docs)
            feature_names = np.array(vectorizer.get_feature_names_out())

            keywords_map = {}
            for idx, lbl in enumerate(cluster_ids):
                row = tfidf_matrix[idx].toarray().flatten()
                top_indices = row.argsort()[::-1][:top_k]
                top_words = [feature_names[i] for i in top_indices if row[i] > 0]
                keywords_map[lbl] = top_words if top_words else ["document", "content"]

            return keywords_map
        except ImportError:
            # Pure Python/NumPy TF-IDF implementation
            return self._pure_tfidf_keywords(cluster_docs, cluster_ids, top_k)
        except Exception as e:
            logger.warning(f"c-TF-IDF keyword extraction error: {e}")
            return {lbl: ["document", "topic"] for lbl in cluster_ids}

    def _pure_tfidf_keywords(
        self, docs: list[str], cluster_ids: list[int], top_k: int
    ) -> dict[int, list[str]]:
        """Zero-dependency mathematical TF-IDF keyword extractor."""
        import math
        import re

        stopwords = {
            "the", "and", "is", "in", "to", "of", "it", "with", "as", "for", "on", "that",
            "this", "are", "from", "at", "by", "an", "be", "or", "was", "which", "will",
            "can", "all", "has", "have", "had", "they", "their", "but", "not", "what",
            "when", "where", "how", "who", "whom", "more", "also", "into", "than", "then",
        }

        # Tokenize and compute term frequencies per document
        doc_tokens = []
        vocab = set()
        for doc in docs:
            tokens = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{3,}\b", doc)
                if w.lower() not in stopwords
            ]
            doc_tokens.append(tokens)
            vocab.update(tokens)

        if not vocab:
            return {lbl: ["general", "content"] for lbl in cluster_ids}

        n_docs = len(docs)
        # Compute Document Frequency (DF)
        df = defaultdict(int)
        for tokens in doc_tokens:
            for term in set(tokens):
                df[term] += 1

        # Compute TF-IDF matrix
        keywords_map = {}
        for lbl, tokens in zip(cluster_ids, doc_tokens, strict=False):
            if not tokens:
                keywords_map[lbl] = ["general", "topic"]
                continue

            tf = defaultdict(int)
            for t in tokens:
                tf[t] += 1

            total_t = len(tokens)
            scores = {}
            for t, count in tf.items():
                term_tf = count / total_t
                term_idf = math.log((1 + n_docs) / (1 + df[t])) + 1.0
                scores[t] = term_tf * term_idf

            sorted_terms = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            top_words = [t for t, _ in sorted_terms[:top_k]]
            keywords_map[lbl] = top_words if top_words else ["document", "topic"]

        return keywords_map

    def _create_single_fallback_topic(
        self, topic_id: int, chunk_ids: list[str], chunk_texts: list[str], X: np.ndarray
    ) -> ClusterTopic:
        """Create a single umbrella topic for tiny collections."""
        kw_map = self._extract_c_tfidf_keywords({topic_id: chunk_texts}, top_k=5)
        keywords = kw_map.get(topic_id, ["general", "documentation"])
        centroid = np.mean(X, axis=0).tolist() if len(X) > 0 else []
        label = " & ".join(keywords[:2]).title() if keywords else "General Knowledge"

        return ClusterTopic(
            topic_id=topic_id,
            label=label,
            keywords=keywords,
            chunk_ids=chunk_ids,
            chunk_count=len(chunk_ids),
            centroid=centroid,
            coherence_score=1.0,
            metadata={"is_outlier": False},
        )

    def analyze_knowledge_gaps(
        self,
        tenant_id: str,
        clustering_result: TopicClusteringResponse,
        chunk_texts: dict[str, str],
    ) -> KnowledgeGapReport:
        """Detect orphaned chunks, sparse clusters, and synthesize vault coverage diagnostics."""
        orphan_ids = []
        sparse_topics = []

        for topic in clustering_result.topics:
            if topic.topic_id == -1:
                orphan_ids.extend(topic.chunk_ids)
            elif topic.chunk_count < 3:
                sparse_topics.append(topic.label)

        total_chunks = max(1, clustering_result.total_chunks)
        connected_chunks = total_chunks - len(orphan_ids)
        coverage_score = round(connected_chunks / total_chunks, 4)

        recommendations = []
        if orphan_ids:
            recommendations.append(
                f"Found {len(orphan_ids)} orphaned or un-clustered chunks. Consider expanding domain context or linking them to related documents."
            )
        if sparse_topics:
            topics_str = ", ".join(sparse_topics[:3])
            recommendations.append(
                f"Topics with sparse documentation (< 3 chunks): {topics_str}. Adding more supporting paragraphs will improve retrieval recall."
            )
        if coverage_score > 0.85:
            recommendations.append("Knowledge vault exhibits high semantic density and strong inter-document clustering.")

        return KnowledgeGapReport(
            tenant_id=tenant_id,
            total_chunks=clustering_result.total_chunks,
            orphan_chunk_count=len(orphan_ids),
            orphan_chunk_ids=orphan_ids,
            sparse_topics=sparse_topics,
            knowledge_coverage_score=coverage_score,
            recommendations=recommendations,
        )
