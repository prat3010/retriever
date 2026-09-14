import { describe, it } from "node:test";
import assert from "node:assert";
import { RetrieverClient } from "../dist/index.js";

describe("RetrieverClient SDK", () => {
  it("should throw when required config parameters are missing", () => {
    assert.throws(
      () => new RetrieverClient({ apiKey: "", baseUrl: "http://localhost:8000", tenantId: "t1" }),
      /requires an apiKey/
    );
    assert.throws(
      () => new RetrieverClient({ apiKey: "key", baseUrl: "", tenantId: "t1" }),
      /requires a baseUrl/
    );
    assert.throws(
      () => new RetrieverClient({ apiKey: "key", baseUrl: "http://localhost:8000", tenantId: "" }),
      /requires a tenantId/
    );
  });

  it("should normalize baseUrl by stripping trailing slashes", () => {
    const client = new RetrieverClient({
      apiKey: "test-key",
      baseUrl: "http://localhost:8000///",
      tenantId: "t1",
    });
    assert.strictEqual(client.baseUrl, "http://localhost:8000");
  });

  it("should format search payload correctly", async () => {
    const originalFetch = globalThis.fetch;
    let capturedUrl = "";
    let capturedBody: any = null;

    globalThis.fetch = async (url: any, init: any) => {
      capturedUrl = url.toString();
      capturedBody = JSON.parse(init.body);
      return {
        ok: true,
        json: async () => ({
          results: [{ chunkId: "c1", content: "Test chunk", score: 0.95, metadata: {} }],
          total: 1,
          latency_ms: 12,
          strategy_used: "hybrid",
          cached: false,
        }),
      } as any;
    };

    try {
      const client = new RetrieverClient({
        apiKey: "ret_live_test_key",
        baseUrl: "http://localhost:8000",
        tenantId: "tenant-uuid-1",
      });

      const res = await client.search("test query", {
        enableColbertRerank: true,
        limit: 3,
      });

      assert.strictEqual(capturedUrl, "http://localhost:8000/v1/tenants/tenant-uuid-1/search");
      assert.strictEqual(capturedBody.query, "test query");
      assert.strictEqual(capturedBody.limit, 3);
      assert.strictEqual(capturedBody.reranker_engine, "colbert");
      assert.strictEqual(res.total, 1);
      assert.strictEqual(res.results[0].chunkId, "c1");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("should fetch connector manifests and trigger sync (Battery #27)", async () => {
    const originalFetch = globalThis.fetch;
    let capturedUrl = "";

    globalThis.fetch = async (url: any) => {
      capturedUrl = url.toString();
      return {
        ok: true,
        json: async () => ({
          manifests: [
            {
              connector_type: "database_cdc",
              name: "Relational Database CDC",
              description: "CDC connector",
              icon: "database",
              supports_incremental: true,
              required_parameters: ["host", "database", "user", "tables"],
              optional_parameters: {},
            },
          ],
          total: 1,
        }),
      } as any;
    };

    try {
      const client = new RetrieverClient({
        apiKey: "ret_live_test_key",
        baseUrl: "http://localhost:8000",
        tenantId: "tenant-uuid-1",
      });

      const manifests = await client.listConnectorManifests();
      assert.strictEqual(capturedUrl, "http://localhost:8000/v1/admin/connectors/manifests");
      assert.strictEqual(manifests.length, 1);
      assert.strictEqual(manifests[0].connector_type, "database_cdc");
      assert.strictEqual(manifests[0].supports_incremental, true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
