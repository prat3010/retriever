/**
 * @prat3010/retriever-client
 * Official TypeScript & JavaScript client SDK for Retriever Enterprise Cognitive Engine (v1.0.0-rc1).
 * 26 Platform Batteries Included:
 * Hybrid Search, ColBERT MaxSim, GraphRAG, NeMo Guardrails, RLM Python REPL,
 * Universal MCP Server, ReAct Tool Loops, Cognitive Memory, Swarm Quorum & Micro-Enclaves.
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

export interface SearchResultItem {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
  latency_ms: number;
  strategy_used: string;
  cached: boolean;
}

export interface ChatOptions {
  xLlmKey?: string;
  stream?: boolean;
  filters?: MetadataFilter[];
  tags?: string[];
  enableQueryRewriting?: boolean;
  enableHybrid?: boolean;
  enableColbertRerank?: boolean;
  enableMemoryGuidance?: boolean;
}

export interface ReActEvent {
  type: "thought" | "tool_call_start" | "tool_call_done" | "token" | "final_answer" | "error";
  content?: string;
  tool_name?: string;
  arguments?: Record<string, any>;
  result?: any;
  step?: number;
  timestamp?: string;
}

export interface CognitiveMemoryNode {
  memory_id: string;
  tenant_id: string;
  category: "episodic" | "procedural" | "factual";
  content: string;
  retention_score: number;
  stability: number;
  created_at: string;
}

export interface SwarmQuorumDebateResult {
  debate_id: string;
  consensus_response: string;
  quorum_confidence: number;
  rounds_evaluated: number;
  participating_roles: string[];
  pruned_hallucinations_count: number;
  consensus_reached: boolean;
}

export interface McpToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
  category: string;
}

export interface EnclaveAttestationEvidence {
  platform: string;
  pcr0: string;
  nonce: string;
  signature: string;
  verified: boolean;
  attested_at: string;
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

export interface ConnectorManifest {
  connector_type: string;
  name: string;
  description: string;
  icon: string;
  supports_incremental: boolean;
  required_parameters: string[];
  optional_parameters: Record<string, any>;
}

export interface ConnectorConfig {
  id: string;
  name: string;
  connector_type: string;
  status: "idle" | "syncing" | "failed" | "disabled";
  sync_interval_minutes: number;
  configuration: Record<string, any>;
  last_sync_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateConnectorPayload {
  name: string;
  connector_type: string;
  sync_interval_minutes?: number;
  configuration?: Record<string, any>;
}

export interface ConnectorSyncResponse {
  connectorId: string;
  status: string;
  documentsDiscovered: number;
  documentsIngested: number;
  durationMs: number;
  message: string;
}

// ── Multimodal Vision GraphRAG Types (Battery #29) ──────────────────────────

export interface VisionBoundingBox {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
  confidence?: number;
}

export interface VisualElement {
  element_id: string;
  label: string;
  element_type: string;
  bounding_box: VisionBoundingBox;
  confidence: number;
  properties?: Record<string, any>;
}

export interface VisualConnector {
  connector_id: string;
  source_element_id: string;
  target_element_id: string;
  label: string;
  directionality: string;
  protocol?: string;
  confidence: number;
}

export interface SchematicDiagram {
  diagram_id: string;
  filename: string;
  document_id?: string;
  page_number: number;
  width: number;
  height: number;
  elements: VisualElement[];
  connectors: VisualConnector[];
  summary: string;
  metadata?: Record<string, any>;
}

export interface MultimodalGraphNode {
  id: string;
  label: string;
  node_type: string;
  element_type?: string;
  bounding_box?: VisionBoundingBox;
  diagram_id?: string;
  document_id?: string;
  metadata?: Record<string, any>;
}

export interface MultimodalGraphEdge {
  source: string;
  target: string;
  relation: string;
  protocol?: string;
  is_cross_modal: boolean;
  confidence: number;
}

export interface MultimodalGraphResponse {
  root_entity: string;
  nodes: MultimodalGraphNode[];
  edges: MultimodalGraphEdge[];
  cross_modal_links_count: number;
  triples_count: number;
  metadata?: Record<string, any>;
}

// ── Voice Streaming & Barge-In (Battery #30 / Milestone 114) ─────────────────

export interface VoiceStreamEvent {
  event_type:
    | "session_ready"
    | "vad_state"
    | "transcript_partial"
    | "transcript_final"
    | "agent_thinking"
    | "agent_text_delta"
    | "interrupted"
    | "turn_complete"
    | "error"
    | "ping"
    | "pong";
  session_id: string;
  payload: Record<string, any>;
}

export interface VoiceStreamCallbacks {
  onSessionReady?: (payload: { codec: string; sample_rate_hz: number; channels: number }) => void;
  onVadState?: (state: "speech_detected" | "endpoint_detected", payload: Record<string, any>) => void;
  onTranscript?: (transcript: { text: string; confidence: number; is_final: boolean; latency_ms?: number }) => void;
  onAgentThinking?: (payload: Record<string, any>) => void;
  onAgentTextDelta?: (delta: string) => void;
  onAgentAudioChunk?: (audioChunk: Uint8Array) => void;
  onInterrupted?: (event: { reason: string; cancelled_turn_id?: string; speech_frames?: number }) => void;
  onTurnComplete?: (turn: Record<string, any>) => void;
  onError?: (error: Error | string) => void;
  onClose?: () => void;
}

export interface VoiceStreamSession {
  sendAudioFrame: (frameBytes: Uint8Array | ArrayBuffer) => void;
  sendTextInput: (text: string) => void;
  interrupt: (reason?: string) => void;
  ping: () => void;
  close: () => void;
}

export class RetrieverClient {
  public readonly apiKey: string;
  public readonly baseUrl: string;
  public readonly tenantId: string;
  public readonly userId?: string;

  constructor(config: RetrieverClientConfig) {
    if (!config.apiKey) throw new Error("RetrieverClient requires an apiKey.");
    if (!config.baseUrl) throw new Error("RetrieverClient requires a baseUrl.");
    if (!config.tenantId) throw new Error("RetrieverClient requires a tenantId.");

    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl.replace(/\/+$/, "");
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

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers = this.getHeaders(
      (options.headers as Record<string, string>) || { "Content-Type": "application/json" }
    );

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Retriever API Error ${response.status}: ${errorText}`);
    }
    return response.json();
  }

  // ── Core Retrieval & Search (Batteries #1, #2, #3) ──────────────────────────

  async search(query: string, options: SearchOptions = {}): Promise<SearchResponse> {
    const payload = {
      query,
      limit: options.limit ?? 10,
      enable_query_rewriting: options.enableQueryRewriting ?? true,
      enable_hybrid: options.enableHybrid ?? true,
      strategy: options.strategy ?? "hybrid",
      hybrid_alpha: options.hybridAlpha ?? 0.7,
      enable_lora_adapter: options.enableLoraAdapter ?? false,
      reranker_engine: options.rerankerEngine ?? (options.enableColbertRerank ? "colbert" : "cohere"),
      filters: options.filters,
      tags: options.tags,
    };

    return this.request<SearchResponse>(`/v1/tenants/${this.tenantId}/search`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // ── Document Ingestion & Management (Battery #4) ───────────────────────────

  async uploadDocument(
    fileData: any,
    filename: string,
    mimeType: string = "application/octet-stream"
  ): Promise<DocumentResponse> {
    const formData = new FormData();
    if (typeof Blob !== "undefined" && fileData instanceof Blob) {
      formData.append("file", fileData, filename);
    } else {
      formData.append("file", fileData, filename);
    }

    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/documents`;
    const headers = this.getHeaders();
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Document upload failed with status ${response.status}: ${await response.text()}`);
    }
    return response.json();
  }

  async listDocuments(limit: number = 50): Promise<DocumentResponse[]> {
    return this.request<DocumentResponse[]>(`/v1/tenants/${this.tenantId}/documents?limit=${limit}`);
  }

  async deleteDocument(documentId: string): Promise<{ success: boolean; document_id: string }> {
    return this.request<{ success: boolean; document_id: string }>(
      `/v1/tenants/${this.tenantId}/documents/${documentId}`,
      { method: "DELETE" }
    );
  }

  // ── Autonomous Multi-Turn ReAct Reasoning Loop (Battery #24) ───────────────

  async *streamReActChat(
    sessionId: string,
    message: string,
    options: ChatOptions = {}
  ): AsyncGenerator<ReActEvent, void, unknown> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages`;
    const payload = {
      content: message,
      stream: true,
      agentic_mode: true,
      enable_memory_guidance: options.enableMemoryGuidance ?? true,
      filters: options.filters,
      tags: options.tags,
    };

    const headers = this.getHeaders({
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    });
    if (options.xLlmKey) {
      headers["X-LLM-Key"] = options.xLlmKey;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      throw new Error(`ReAct stream failed with status ${response.status}: ${await response.text()}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const dataStr = trimmed.replace(/^data:\s*/, "");
        if (dataStr === "[DONE]") return;

        try {
          const parsed = JSON.parse(dataStr);
          yield parsed as ReActEvent;
        } catch {
          yield { type: "token", content: dataStr };
        }
      }
    }
  }

  // ── Cognitive Agent Memory Consolidation (Battery #25) ─────────────────────

  async queryCognitiveMemory(query: string, limit: number = 5): Promise<CognitiveMemoryNode[]> {
    return this.request<CognitiveMemoryNode[]>(
      `/v1/tenants/${this.tenantId}/memory/query`,
      {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      }
    );
  }

  async synthesizeMemoryExperience(sessionId: string): Promise<{ success: boolean; distilled_count: number }> {
    return this.request<{ success: boolean; distilled_count: number }>(
      `/v1/tenants/${this.tenantId}/memory/distill`,
      {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      }
    );
  }

  // ── Multi-Agent Swarm Quorum & Dialectic Debate (Battery #26) ───────────────

  async executeSwarmDebate(
    task: string,
    roles: string[] = ["planner", "auditor", "synthesizer", "skeptic"],
    rounds: number = 2
  ): Promise<SwarmQuorumDebateResult> {
    return this.request<SwarmQuorumDebateResult>(
      `/v1/tenants/${this.tenantId}/swarm/debate`,
      {
        method: "POST",
        body: JSON.stringify({ task, roles, max_rounds: rounds }),
      }
    );
  }

  // ── Universal Model Context Protocol (MCP) Server (Battery #23) ────────────

  async listMcpTools(): Promise<McpToolDefinition[]> {
    const res = await this.request<{ tools: McpToolDefinition[] }>("/v1/mcp/tools");
    return res.tools;
  }

  async callMcpTool(name: string, argumentsPayload: Record<string, any> = {}): Promise<any> {
    return this.request<any>("/v1/mcp/messages", {
      method: "POST",
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: "mcp-call-1",
        method: "tools/call",
        params: { name, arguments: argumentsPayload },
      }),
    });
  }

  // ── Zero-Trust Micro-Enclave Encryption & Attestation (Battery #21) ────────

  async getEnclaveAttestation(challengeNonce?: string): Promise<EnclaveAttestationEvidence> {
    return this.request<EnclaveAttestationEvidence>(
      `/v1/tenants/${this.tenantId}/enclave/attestation`,
      {
        method: "POST",
        body: JSON.stringify({ challenge_nonce: challengeNonce }),
      }
    );
  }

  async sealMemoryEnclave(data: string): Promise<{ ciphertext: string; tag: string; pcr_bound: boolean }> {
    return this.request<{ ciphertext: string; tag: string; pcr_bound: boolean }>(
      `/v1/tenants/${this.tenantId}/enclave/seal`,
      {
        method: "POST",
        body: JSON.stringify({ plaintext: data }),
      }
    );
  }

  // ── Recursive Language Model (RLM) Code Execution (Battery #5) ─────────────

  async executeRlmCode(prompt: string, maxDepth: number = 3): Promise<any> {
    return this.request<any>("/v1/rlm/execute", {
      method: "POST",
      body: JSON.stringify({ prompt, depth: maxDepth }),
    });
  }

  // ── Community Connectors & CDC Pipeline (Battery #27) ──────────────────────

  async listConnectorManifests(): Promise<ConnectorManifest[]> {
    const res = await this.request<{ manifests: ConnectorManifest[]; total: number }>(
      "/v1/admin/connectors/manifests"
    );
    return res.manifests;
  }

  async listConnectors(): Promise<ConnectorConfig[]> {
    return this.request<ConnectorConfig[]>(`/v1/admin/tenants/${this.tenantId}/connectors`);
  }

  async createConnector(payload: CreateConnectorPayload): Promise<ConnectorConfig> {
    return this.request<ConnectorConfig>(`/v1/admin/tenants/${this.tenantId}/connectors`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async triggerConnectorSync(connectorId: string): Promise<ConnectorSyncResponse> {
    return this.request<ConnectorSyncResponse>(
      `/v1/admin/tenants/${this.tenantId}/connectors/${connectorId}/sync`,
      {
        method: "POST",
      }
    );
  }

  // ── Multimodal Vision GraphRAG & Schematic Ingestion (Battery #29) ─────────

  async extractSchematicText(
    content: string,
    filename: string = "architecture.svg",
    documentId?: string
  ): Promise<SchematicDiagram> {
    return this.request<SchematicDiagram>(
      `/v1/tenants/${this.tenantId}/vision/schematic/extract-text`,
      {
        method: "POST",
        body: JSON.stringify({ content, filename, document_id: documentId }),
      }
    );
  }

  async queryMultimodalGraph(
    entityQuery: string,
    maxHops: number = 2
  ): Promise<MultimodalGraphResponse> {
    return this.request<MultimodalGraphResponse>(
      `/v1/tenants/${this.tenantId}/vision/graph/query`,
      {
        method: "POST",
        body: JSON.stringify({
          tenant_id: this.tenantId,
          entity_query: entityQuery,
          max_hops: maxHops,
          include_visual_boxes: true,
        }),
      }
    );
  }

  async getDocumentSchematics(documentId: string): Promise<{ document_id: string; total_triples: number; triples: any[] }> {
    return this.request<{ document_id: string; total_triples: number; triples: any[] }>(
      `/v1/tenants/${this.tenantId}/vision/schematics/${documentId}`
    );
  }

  async getMultimodalVisionStatus(): Promise<{ battery_id: string; status: string; version: string; milestone: string }> {
    return this.request<{ battery_id: string; status: string; version: string; milestone: string }>(
      "/v1/graph/multimodal/status"
    );
  }

  // ── Voice Streaming & Real-Time Audio (Battery #30 / Milestone 114) ────────

  createVoiceStream(
    sessionId: string,
    callbacks: VoiceStreamCallbacks,
    options?: {
      sensitivity?: number;
      silenceThresholdMs?: number;
      voice?: string;
      speed?: number;
    }
  ): VoiceStreamSession {
    const wsProto = this.baseUrl.startsWith("https") ? "wss" : "ws";
    const host = this.baseUrl.replace(/^https?:\/\//, "").replace(/\/+$/, "");
    const params = new URLSearchParams({
      token: this.apiKey,
      sensitivity: String(options?.sensitivity ?? 0.65),
      silence_threshold_ms: String(options?.silenceThresholdMs ?? 400),
      voice: options?.voice ?? "neural_natural",
      speed: String(options?.speed ?? 1.0),
    });
    const url = `${wsProto}://${host}/v1/tenants/${this.tenantId}/voice/stream/${sessionId}?${params.toString()}`;

    const WebSocketImpl = typeof WebSocket !== "undefined" ? WebSocket : (globalThis as any).WebSocket;
    if (!WebSocketImpl) {
      throw new Error("WebSocket implementation not found in global scope");
    }

    const ws = new WebSocketImpl(url);
    ws.binaryType = "arraybuffer";

    ws.onmessage = (event: any) => {
      if (typeof event.data === "string") {
        try {
          const msg: VoiceStreamEvent = JSON.parse(event.data);
          switch (msg.event_type) {
            case "session_ready":
              callbacks.onSessionReady?.(msg.payload as any);
              break;
            case "vad_state":
              callbacks.onVadState?.(msg.payload?.state, msg.payload);
              break;
            case "transcript_partial":
            case "transcript_final":
              callbacks.onTranscript?.({
                text: msg.payload?.text,
                confidence: msg.payload?.confidence,
                is_final: msg.event_type === "transcript_final",
                latency_ms: msg.payload?.latency_ms,
              });
              break;
            case "agent_thinking":
              callbacks.onAgentThinking?.(msg.payload);
              break;
            case "agent_text_delta":
              callbacks.onAgentTextDelta?.(msg.payload?.delta || "");
              break;
            case "interrupted":
              callbacks.onInterrupted?.(msg.payload as any);
              break;
            case "turn_complete":
              callbacks.onTurnComplete?.(msg.payload?.turn);
              break;
            case "error":
              callbacks.onError?.(msg.payload?.error || "Unknown stream error");
              break;
          }
        } catch (e: any) {
          callbacks.onError?.(e);
        }
      } else if (event.data instanceof ArrayBuffer || ArrayBuffer.isView(event.data)) {
        const chunk = event.data instanceof ArrayBuffer ? new Uint8Array(event.data) : new Uint8Array(event.data.buffer);
        callbacks.onAgentAudioChunk?.(chunk);
      }
    };

    ws.onerror = (err: any) => {
      callbacks.onError?.(err);
    };

    ws.onclose = () => {
      callbacks.onClose?.();
    };

    return {
      sendAudioFrame: (frameBytes: Uint8Array | ArrayBuffer) => {
        if (ws.readyState === (ws.OPEN ?? 1)) {
          ws.send(frameBytes);
        }
      },
      sendTextInput: (text: string) => {
        if (ws.readyState === (ws.OPEN ?? 1)) {
          ws.send(JSON.stringify({ event_type: "text_input", text }));
        }
      },
      interrupt: (reason: string = "client_interrupt") => {
        if (ws.readyState === (ws.OPEN ?? 1)) {
          ws.send(JSON.stringify({ event_type: "interrupt", reason }));
        }
      },
      ping: () => {
        if (ws.readyState === (ws.OPEN ?? 1)) {
          ws.send(JSON.stringify({ event_type: "ping" }));
        }
      },
      close: () => {
        ws.close();
      },
    };
  }
}
