/**
 * HTTP Client for Retriever Cognitive Engine (https://rag.prateeq.in)
 */

import { readdirSync, readFileSync } from "node:fs";
import { basename, extname, join } from "node:path";

export interface RetrieverClientOptions {
  baseUrl?: string;
  adminMasterKey?: string;
  defaultTenantId?: string;
  apiKey?: string;
}

export interface DirectoryIngestOptions {
  extensions?: string[];
  recursive?: boolean;
  maxFiles?: number;
}

export interface DirectoryIngestResult {
  directoryPath: string;
  totalFound: number;
  totalIngested: number;
  failedCount: number;
  files: Array<{
    file: string;
    documentId?: string;
    status: string;
    error?: string;
  }>;
}

export interface TenantInfo {
  tenantId: string;
  name: string;
  status: string;
  tier: string;
  createdAt: string;
}

export interface PaginatedTenants {
  items: TenantInfo[];
  total: number;
}

export interface ApiKeyInfo {
  apiKey: string;
  keyId: string;
  tenantId: string;
  prefix: string;
  role: string;
  status: string;
}

export interface DocumentInfo {
  documentId: string;
  filename: string;
  status: string;
  chunkCount?: number;
  fileSize?: number;
  createdAt: string;
}

export interface SearchResult {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export class RetrieverClient {
  private baseUrl: string;
  private adminMasterKey?: string;
  private defaultTenantId?: string;
  private apiKey?: string;

  constructor(options: RetrieverClientOptions = {}) {
    this.baseUrl = (options.baseUrl || process.env.RETRIEVER_API_URL || "https://rag.prateeq.in").replace(/\/+$/, "");
    this.adminMasterKey = options.adminMasterKey || process.env.RETRIEVER_ADMIN_MASTER_KEY;
    this.defaultTenantId = options.defaultTenantId || process.env.RETRIEVER_TENANT_ID;
    this.apiKey = options.apiKey || process.env.RETRIEVER_API_KEY;
  }

  private getHeaders(useAdmin = false): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: "application/json",
    };

    if (useAdmin && this.adminMasterKey) {
      headers["X-Admin-Master-Key"] = this.adminMasterKey;
    } else if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
      headers["X-User-ID"] = "mcp_agent";
    } else if (this.adminMasterKey) {
      // Fallback: master key also bypasses RLS
      headers["X-Admin-Master-Key"] = this.adminMasterKey;
      headers["X-User-ID"] = "mcp_agent";
    }

    return headers;
  }

  // ── Admin Suite ────────────────────────────────────────────────────────────

  async getSystemHealth(): Promise<{
    status: string;
    baseUrl: string;
    readiness: any;
    liveness: any;
    timestamp: string;
  }> {
    let readiness: any = null;
    let liveness: any = null;

    try {
      const r = await fetch(`${this.baseUrl}/health/readiness`, {
        headers: { Accept: "application/json" },
      });
      if (r.ok) readiness = await r.json();
      else readiness = { status: "degraded", httpStatus: r.status };
    } catch (err: any) {
      readiness = { status: "unreachable", error: err.message };
    }

    try {
      const l = await fetch(`${this.baseUrl}/health/liveness`, {
        headers: { Accept: "application/json" },
      });
      if (l.ok) liveness = await l.json();
      else liveness = { status: "degraded", httpStatus: l.status };
    } catch (err: any) {
      liveness = { status: "unreachable", error: err.message };
    }

    const isHealthy =
      readiness?.status === "ready" ||
      readiness?.status === "ok" ||
      liveness?.status === "ok";

    return {
      status: isHealthy ? "healthy" : "degraded",
      baseUrl: this.baseUrl,
      readiness,
      liveness,
      timestamp: new Date().toISOString(),
    };
  }

  async createTenant(name: string, tier = "standard"): Promise<TenantInfo> {
    const res = await fetch(`${this.baseUrl}/v1/tenants`, {
      method: "POST",
      headers: {
        ...this.getHeaders(true),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name, tier }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to create tenant (${res.status}): ${err}`);
    }

    return res.json();
  }

  async listTenants(limit = 50, search?: string): Promise<PaginatedTenants> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (search) params.set("search", search);

    const res = await fetch(`${this.baseUrl}/v1/admin/tenants?${params}`, {
      method: "GET",
      headers: this.getHeaders(true),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to list tenants (${res.status}): ${err}`);
    }

    return res.json();
  }

  async getTenant(tenantId: string): Promise<TenantInfo> {
    const res = await fetch(`${this.baseUrl}/v1/admin/tenants/${tenantId}`, {
      method: "GET",
      headers: this.getHeaders(true),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to get tenant (${res.status}): ${err}`);
    }

    return res.json();
  }

  async issueApiKey(tenantId: string, name: string, role: "client" | "admin" = "client"): Promise<ApiKeyInfo> {
    const res = await fetch(`${this.baseUrl}/v1/admin/tenants/${tenantId}/api-keys`, {
      method: "POST",
      headers: {
        ...this.getHeaders(true),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name, role }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to issue API key (${res.status}): ${err}`);
    }

    return res.json();
  }

  // ── Document Ingestion Suite ───────────────────────────────────────────────

  async ingestText(
    tenantId: string,
    filename: string,
    content: string,
    tags: string[] = []
  ): Promise<{ documentId: string; status: string; message: string }> {
    const formData = new FormData();
    const blob = new Blob([content], { type: "text/markdown" });
    formData.append("file", blob, filename);
    if (tags.length > 0) {
      formData.append("tags", JSON.stringify(tags));
    }

    const res = await fetch(`${this.baseUrl}/v1/admin/tenants/${tenantId}/documents/upload`, {
      method: "POST",
      headers: this.getHeaders(true),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to ingest text (${res.status}): ${err}`);
    }

    return res.json();
  }

  async uploadFile(tenantId: string, filePath: string): Promise<{ documentId: string; status: string }> {
    const fileBytes = readFileSync(filePath);
    const fileName = basename(filePath);
    const formData = new FormData();
    const blob = new Blob([fileBytes]);
    formData.append("file", blob, fileName);

    const res = await fetch(`${this.baseUrl}/v1/admin/tenants/${tenantId}/documents/upload`, {
      method: "POST",
      headers: this.getHeaders(true),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to upload file (${res.status}): ${err}`);
    }

    return res.json();
  }

  async listDocuments(tenantId: string, limit = 50): Promise<DocumentInfo[]> {
    const res = await fetch(`${this.baseUrl}/v1/admin/tenants/${tenantId}/documents?limit=${limit}`, {
      method: "GET",
      headers: this.getHeaders(true),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to list documents (${res.status}): ${err}`);
    }

    const data = await res.json();
    return Array.isArray(data) ? data : data.items || [];
  }

  async ingestDirectory(
    tenantId: string,
    dirPath: string,
    options: DirectoryIngestOptions = {}
  ): Promise<DirectoryIngestResult> {
    const targetExts = new Set(
      (options.extensions || [".md", ".txt", ".pdf", ".json", ".csv"]).map((e) =>
        e.startsWith(".") ? e.toLowerCase() : `.${e.toLowerCase()}`
      )
    );
    const recursive = options.recursive !== false;
    const maxFiles = options.maxFiles || 100;

    const ignoreDirs = new Set([
      ".git",
      "node_modules",
      ".next",
      "dist",
      "__pycache__",
      ".venv",
      "venv",
      ".pytest_cache",
      ".ruff_cache",
    ]);

    const collectedFiles: string[] = [];

    function scan(currentDir: string) {
      if (collectedFiles.length >= maxFiles) return;
      const entries = readdirSync(currentDir, { withFileTypes: true });
      for (const entry of entries) {
        if (collectedFiles.length >= maxFiles) break;
        const fullPath = join(currentDir, entry.name);
        if (entry.isDirectory()) {
          if (recursive && !ignoreDirs.has(entry.name) && !entry.name.startsWith(".")) {
            scan(fullPath);
          }
        } else if (entry.isFile()) {
          const ext = extname(entry.name).toLowerCase();
          if (targetExts.has(ext)) {
            collectedFiles.push(fullPath);
          }
        }
      }
    }

    scan(dirPath);

    const results: DirectoryIngestResult = {
      directoryPath: dirPath,
      totalFound: collectedFiles.length,
      totalIngested: 0,
      failedCount: 0,
      files: [],
    };

    for (const filePath of collectedFiles) {
      try {
        const uploadRes = await this.uploadFile(tenantId, filePath);
        results.totalIngested++;
        results.files.push({
          file: basename(filePath),
          documentId: uploadRes.documentId,
          status: uploadRes.status,
        });
      } catch (err: any) {
        results.failedCount++;
        results.files.push({
          file: basename(filePath),
          status: "failed",
          error: err.message,
        });
      }
    }

    return results;
  }

  // ── Cognitive Suite ────────────────────────────────────────────────────────

  async hybridSearch(
    tenantId: string,
    query: string,
    topK = 5,
    filters?: Record<string, any>
  ): Promise<SearchResult[]> {
    const res = await fetch(`${this.baseUrl}/v1/tenants/${tenantId}/search`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        limit: topK,
        filters: filters || [],
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to execute hybrid search (${res.status}): ${err}`);
    }

    return res.json();
  }

  async createGotPlan(
    tenantId: string,
    prompt: string,
    branchingFactor = 3
  ): Promise<any> {
    const res = await fetch(`${this.baseUrl}/v1/tenants/${tenantId}/got/plans`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: prompt,
        branching_factor: branchingFactor,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to create GoT plan (${res.status}): ${err}`);
    }

    return res.json();
  }
}
