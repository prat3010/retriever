"""Multi-Tenant Production Load Testing Suite with Realistic User Profiles.

Simulates concurrent tenant traffic across Hybrid Search, Semantic Caching,
SSE Streaming Chat, Document Querying, and Topic Modeling.
"""

import os
import random

from locust import HttpUser, between, task

DEMO_TENANT_ID = os.getenv("LOAD_TEST_TENANT_ID", "1f85286c-9d9a-4ebc-9c62-a99360a5ece4")
DEMO_API_KEY = os.getenv("LOAD_TEST_API_KEY", "ret_live_hUQ-4muveDE.w9aBPR9iJBMbWeaUapCwUR-_T9IlwmXh")
DEMO_USER_ID = os.getenv("LOAD_TEST_USER_ID", "36e62429-419e-48ef-af92-533afca9e028")

SAMPLE_QUERIES = [
    "What are the payment terms and refund policies?",
    "Explain the architecture of the distributed vector database.",
    "How does the Llama Guard 3 safety filter prevent prompt injection?",
    "What is the SLA turnaround time for Phase 1 deliverables?",
    "Summarize the technical specifications for the hybrid search reranker.",
    "How does the zero-trust AES-256 field encryption work?",
    "What are the prerequisites for the Google OAuth fast-pass flow?",
    "Compare pgvector HNSW indexing versus BM25 full text search.",
    "Where is the semantic cache stored and what is the latency reduction?",
    "How do change orders calculate milestone payment deltas?",
]


class TenantSearchUser(HttpUser):
    """Simulates active client search queries testing Dense/Sparse fusion and Semantic Cache."""

    wait_time = between(0.5, 2.0)
    weight = 5

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {DEMO_API_KEY}",
            "X-User-ID": DEMO_USER_ID,
            "Content-Type": "application/json",
        }

    @task(3)
    def search_hybrid(self):
        query = random.choice(SAMPLE_QUERIES)
        payload = {
            "query": query,
            "limit": 5,
            "enable_hybrid": True,
            "enable_rerank": True,
        }
        with self.client.post(
            f"/v1/tenants/{DEMO_TENANT_ID}/search",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/v1/tenants/[id]/search",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed with status {response.status_code}")

    @task(1)
    def search_cached_repeated(self):
        """Repeats identical query to measure semantic cache response time."""
        payload = {
            "query": SAMPLE_QUERIES[0],
            "limit": 3,
            "enable_hybrid": True,
        }
        with self.client.post(
            f"/v1/tenants/{DEMO_TENANT_ID}/search",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/v1/tenants/[id]/search (Cache Probe)",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache probe failed with status {response.status_code}")


class TenantChatUser(HttpUser):
    """Simulates real-time interactive chat sessions and citation queries."""

    wait_time = between(1.0, 3.5)
    weight = 3

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {DEMO_API_KEY}",
            "X-User-ID": DEMO_USER_ID,
            "Content-Type": "application/json",
        }

    @task(2)
    def chat_query(self):
        query = random.choice(SAMPLE_QUERIES)
        payload = {
            "query": query,
            "stream": False,
            "enable_guardrails": True,
            "enable_compression": True,
        }
        with self.client.post(
            f"/v1/tenants/{DEMO_TENANT_ID}/chat",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/v1/tenants/[id]/chat",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Chat failed with status {response.status_code}")


class TenantDocumentUser(HttpUser):
    """Simulates document inventory queries and platform health checks."""

    wait_time = between(2.0, 5.0)
    weight = 2

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {DEMO_API_KEY}",
            "X-User-ID": DEMO_USER_ID,
        }

    @task(2)
    def list_documents(self):
        with self.client.get(
            f"/v1/tenants/{DEMO_TENANT_ID}/documents",
            headers=self.headers,
            catch_response=True,
            name="/v1/tenants/[id]/documents",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List docs failed with status {response.status_code}")

    @task(1)
    def health_readiness(self):
        with self.client.get(
            "/health/readiness",
            catch_response=True,
            name="/health/readiness",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status {response.status_code}")
