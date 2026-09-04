/**
 * @prat3010/retriever-client-js
 * Official TypeScript client SDK for Retriever AI Engine (v0.79.0).
 * Supports Hybrid Search, Streaming Chat, NeMo Guardrails, DSPy Prompt Optimization,
 * RLM Python REPL, Multi-Agent Consensus, and Cognitive Telemetry.
 */

export interface RetrieverClientConfig {
  apiKey: string;
  baseUrl: string;
  tenantId: string;
  userId?: string;
}

export interface MetadataFilter {
  field: string;
  operator: "eq" | "neq" | "in" | "gt" | "gte" | "lt" | "lte" | "exists" | "contains" | "regex";
  value: any;
}

export interface SearchOptions {
  limit?: number;
  enableQueryRewriting?: boolean;
  enableHybrid?: boolean;
  strategy?: string;
  hybridAlpha?: number;
  enableLoraAdapter?: boolean;
  rerankerEngine?: "cohere" | "colbert" | "none";
  enableColbertRerank?: boolean;
  filters?: MetadataFilter[];
  tags?: string[];
}

export interface ChatOptions {
  xLlmKey?: string;
  stream?: boolean;
  filters?: MetadataFilter[];
  tags?: string[];
  enableQueryRewriting?: boolean;
  enableHybrid?: boolean;
  enableColbertRerank?: boolean;
}

export interface PaginationOptions {
  limit?: number;
  cursor?: string;
}

export interface PaginationMeta {
  nextCursor: string | null;
  limit: number;
  hasMore: boolean;
}

export interface PaginatedResult<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface DocumentResponse {
  documentId: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface SearchResultItem {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface ChatMessageResponse {
  messageId: string;
  sessionId: string;
  tenantId: string;
  role: string;
  content: string;
  name: string | null;
  createdAt: string;
}

// ── NeMo Guardrails Types ───────────────────────────────────────────────────

export type GuardrailExecutionMode =
  | "disabled"
  | "input_only"
  | "output_grounding_only"
  | "full_conversational";

export interface ColangFlowDefinition {
  name: string;
  user_intent: string;
  bot_response: string;
  priority: number;
}

export interface GuardrailRule {
  rule_id: string;
  name: string;
  category: string;
  enabled: boolean;
  threshold?: number;
}

export interface TenantGuardrailsConfig {
  tenant_id: string;
  mode: GuardrailExecutionMode;
  colang_script: string;
  active_flows: ColangFlowDefinition[];
  rules: GuardrailRule[];
  pii_redaction_enabled: boolean;
  competitor_shield_enabled: boolean;
  competitor_names: string[];
  brand_tone: string;
  grounding_threshold: number;
  fallback_response: string;
  updated_at: string;
}

export interface GuardrailViolation {
  rule_id: string;
  rail_type: string;
  action_taken: "block" | "steer" | "warn" | "log";
  reason: string;
  matched_pattern?: string | null;
  latency_ms: number;
  timestamp: string;
}

export interface GuardrailCheckResult {
  passed: boolean;
  action: "allow" | "block" | "steer";
  violations: GuardrailViolation[];
  steered_response?: string | null;
  fast_path_matched: boolean;
  latency_ms: number;
}

export interface ColangTemplate {
  name: string;
  description: string;
  colang: string;
  rules: Array<{
    rule_id: string;
    name: string;
    category: string;
    enabled: boolean;
  }>;
}

export interface GuardrailTelemetry {
  tenant_id: string;
  total_violations: number;
  total_blocked: number;
  total_steered: number;
  recent_violations: GuardrailViolation[];
  average_rail_latency_ms: number;
}

// ── RLM & Cognitive Types ───────────────────────────────────────────────────

export interface RlmCodeExecution {
  step: number;
  code_snippet: string;
  output: string;
  execution_error?: string | null;
}

export interface RlmAnalysisResult {
  prompt: string;
  depth: number;
  analysis_summary: string;
  code_executions?: RlmCodeExecution[];
  subcalls_count: number;
  execution_time_ms: number;
}

export interface ConsensusResult {
  consensus_response: string;
  agreement_score: number;
  rounds_evaluated: number;
  rationale: string;
  evaluations: Array<{
    critic_id: string;
    score: number;
    critique: string;
  }>;
}

// ── Client Class ─────────────────────────────────────────────────────────────

export class RetrieverClient {
  private apiKey: string;
  private baseUrl: string;
  private tenantId: string;
  private userId?: string;

  constructor(config: RetrieverClientConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.tenantId = config.tenantId;
    this.userId = config.userId;
  }

  private getHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      "X-API-Key": this.apiKey,
      "Authorization": `Bearer ${this.apiKey}`,
      ...customHeaders,
    };
    if (this.userId) {
      headers["X-User-ID"] = this.userId;
    }
    return headers;
  }

  // ── Document Operations ───────────────────────────────────────────────────

  async uploadDocument(
    fileData: any,
    filename: string,
    mimeType: string = "application/octet-stream",
    idempotencyKey?: string
  ): Promise<any> {
    const formData = new FormData();

    if (typeof Blob !== "undefined" && fileData instanceof Blob) {
      formData.append("file", fileData, filename);
    } else if (fileData && typeof fileData === "object" && fileData.constructor && fileData.constructor.name === "Buffer") {
      const blob = new Blob([fileData], { type: mimeType });
      formData.append("file", blob, filename);
    } else {
      formData.append("file", fileData, filename);
    }

    const headers = this.getHeaders();
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/documents`;
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async listDocuments(options: PaginationOptions = {}): Promise<PaginatedResult<DocumentResponse> | DocumentResponse[]> {
    const params = new URLSearchParams();
    if (options.limit !== undefined) {
      params.append("limit", options.limit.toString());
    }
    if (options.cursor) {
      params.append("cursor", options.cursor);
    }

    const queryStr = params.toString();
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/documents${queryStr ? "?" + queryStr : ""}`;

    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async deleteDocument(documentId: string): Promise<any> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/documents/${documentId}`;
    const response = await fetch(url, {
      method: "DELETE",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async getPresignedDownloadUrl(documentId: string): Promise<{ download_url: string; expires_in: number }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/documents/${documentId}/download`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  // ── Search & Retrieval ────────────────────────────────────────────────────

  async search(query: string, options: SearchOptions = {}): Promise<{ results: SearchResultItem[]; searchMeta: { durationMs: number } }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/search`;
    const body: Record<string, any> = {
      query,
      limit: options.limit || 5,
      enable_query_rewriting: options.enableQueryRewriting,
      enable_hybrid: options.enableHybrid,
      strategy: options.strategy,
      hybrid_alpha: options.hybridAlpha,
      enable_lora_adapter: options.enableLoraAdapter,
      reranker_engine: options.rerankerEngine,
      enable_colbert_rerank: options.enableColbertRerank,
    };
    if (options.filters && options.filters.length > 0) {
      body.filters = options.filters;
    }
    if (options.tags && options.tags.length > 0) {
      body.tags = options.tags;
    }

    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  // ── Sessions & Chat ───────────────────────────────────────────────────────

  async createSession(): Promise<{ sessionId: string }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async listMessages(sessionId: string, options: PaginationOptions = {}): Promise<PaginatedResult<ChatMessageResponse>> {
    const params = new URLSearchParams();
    if (options.limit !== undefined) {
      params.append("limit", options.limit.toString());
    }
    if (options.cursor) {
      params.append("cursor", options.cursor);
    }

    const queryStr = params.toString();
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages${queryStr ? "?" + queryStr : ""}`;

    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async chat(sessionId: string, message: string, options: ChatOptions = {}): Promise<any> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages`;
    const headers = this.getHeaders({ "Content-Type": "application/json" });
    if (options.xLlmKey) {
      headers["X-LLM-Key"] = options.xLlmKey;
    }

    const body: Record<string, any> = {
      query: message,
      stream: false,
      enable_query_rewriting: options.enableQueryRewriting,
      enable_hybrid: options.enableHybrid,
      enable_colbert_rerank: options.enableColbertRerank,
    };
    if (options.filters && options.filters.length > 0) {
      body.filters = options.filters;
    }
    if (options.tags && options.tags.length > 0) {
      body.tags = options.tags;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async *chatStream(sessionId: string, message: string, options: ChatOptions = {}): AsyncGenerator<any, void, unknown> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages`;
    const headers = this.getHeaders({
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    });
    if (options.xLlmKey) {
      headers["X-LLM-Key"] = options.xLlmKey;
    }

    const body: Record<string, any> = {
      query: message,
      stream: true,
      enable_query_rewriting: options.enableQueryRewriting,
      enable_hybrid: options.enableHybrid,
      enable_colbert_rerank: options.enableColbertRerank,
    };
    if (options.filters && options.filters.length > 0) {
      body.filters = options.filters;
    }
    if (options.tags && options.tags.length > 0) {
      body.tags = options.tags;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6).trim();
            try {
              yield JSON.parse(dataStr);
            } catch {
              yield dataStr;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async submitMessageFeedback(sessionId: string, messageId: string, rating: "thumbs_up" | "thumbs_down", comment?: string): Promise<any> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages/${messageId}/feedback`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ rating, comment }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  // ── Cognitive Labs: RLM & Consensus ───────────────────────────────────────

  async runRlmAnalysis(prompt: string, maxDepth = 2): Promise<RlmAnalysisResult> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/rlm/analyze`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ prompt, max_depth: maxDepth }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async runMultiAgentConsensus(task: string, candidateResponses: string[]): Promise<ConsensusResult> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/agentic/consensus`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ task, candidate_responses: candidateResponses }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  // ── Semantic Cache ────────────────────────────────────────────────────────

  async getSemanticCacheStats(): Promise<{ status: string; total_vectors: number }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/cache/stats`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async purgeSemanticCache(): Promise<{ status: string; purged: boolean; deleted_count?: number }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/cache/purge`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  // ── NVIDIA NeMo Guardrails ────────────────────────────────────────────────

  async getGuardrailTemplates(): Promise<Record<string, ColangTemplate>> {
    const url = `${this.baseUrl}/v1/guardrails/templates`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async getGuardrailConfig(): Promise<TenantGuardrailsConfig> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/config`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async updateGuardrailConfig(payload: Partial<TenantGuardrailsConfig>): Promise<TenantGuardrailsConfig> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/config`;
    const response = await fetch(url, {
      method: "PUT",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async validateGuardrailInput(query: string, history?: Array<{ role: string; content: string }>): Promise<GuardrailCheckResult> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/validate-input`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ query, conversation_history: history }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async validateGuardrailOutput(query: string, generatedResponse: string, retrievedContexts: string[] = []): Promise<GuardrailCheckResult> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/validate-output`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        query,
        generated_response: generatedResponse,
        retrieved_contexts: retrievedContexts,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async testGuardrailFlow(query: string, customColang?: string): Promise<GuardrailCheckResult> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/test-flow`;
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ query, custom_colang: customColang }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async getGuardrailTelemetry(): Promise<GuardrailTelemetry> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/guardrails/telemetry`;
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders({ "Content-Type": "application/json" }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }
}
