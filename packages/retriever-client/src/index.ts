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

  // ── Distributed Model Context Protocol (MCP) Mesh & Agent Federation (Battery #30) ────

  async getMeshStatus(): Promise<MeshStatusSummary> {
    return this.request<MeshStatusSummary>("/v1/mesh/status");
  }

  async listMeshNodes(statusFilter?: MeshNodeStatus): Promise<MeshPeerNode[]> {
    const query = statusFilter ? `?status=${statusFilter}` : "";
    return this.request<MeshPeerNode[]>(`/v1/mesh/nodes${query}`);
  }

  async registerMeshNode(node: Partial<MeshPeerNode> & { node_id: string; cluster_id: string; endpoint_url: string }): Promise<MeshPeerNode> {
    return this.request<MeshPeerNode>("/v1/mesh/nodes/register", {
      method: "POST",
      body: JSON.stringify(node),
    });
  }

  async sendMeshHeartbeat(nodeId: string, latencyMs?: number): Promise<MeshPeerNode> {
    return this.request<MeshPeerNode>("/v1/mesh/nodes/heartbeat", {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId, latency_ms: latencyMs }),
    });
  }

  async listMeshTools(): Promise<any[]> {
    return this.request<any[]>("/v1/mesh/tools");
  }

  async executeMeshTool(
    toolName: string,
    args: Record<string, any> = {},
    targetClusterId: string = "cluster_local",
    policy: MeshRoutingPolicy = "local_first"
  ): Promise<any> {
    return this.request<any>(`/v1/mesh/tools/execute?policy=${policy}`, {
      method: "POST",
      body: JSON.stringify({
        call_id: `call_${Math.random().toString(36).slice(2, 10)}`,
        tool_name: toolName,
        arguments: args,
        tenant_id: this.tenantId,
        source_cluster_id: "cluster_client_sdk",
        target_cluster_id: targetClusterId,
      }),
    });
  }

  async delegateFederatedTask(request: {
    target_cluster_id: string;
    intent: string;
    target_agent_role?: string;
    context_scope?: Record<string, any>;
    max_depth?: number;
    visited_clusters?: string[];
  }): Promise<FederatedDelegationResponse> {
    return this.request<FederatedDelegationResponse>("/v1/mesh/federation/delegate", {
      method: "POST",
      body: JSON.stringify({
        target_cluster_id: request.target_cluster_id,
        tenant_id: this.tenantId,
        intent: request.intent,
        target_agent_role: request.target_agent_role ?? "forensic_auditor",
        context_scope: request.context_scope ?? {},
        max_depth: request.max_depth ?? 2,
        visited_clusters: request.visited_clusters ?? [],
      }),
    });
  }

  async getFederatedTaskStatus(delegationId: string): Promise<FederatedDelegationResponse> {
    return this.request<FederatedDelegationResponse>(`/v1/mesh/federation/tasks/${delegationId}`);
  }

  // ── Autonomous Mesh Dynamic Load-Balancing & Autoscaling (Battery #31 / M116) ──

  async getMeshLoadMetrics(): Promise<ClusterLoadSummary> {
    return this.request<ClusterLoadSummary>("/v1/mesh/load/metrics");
  }

  async getAutoscalingEvents(limit: number = 50): Promise<AutoscalingEvent[]> {
    return this.request<AutoscalingEvent[]>(`/v1/mesh/load/autoscaling/events?limit=${limit}`);
  }

  async updateAutoscalingPolicy(policy: AutoscalingPolicy): Promise<AutoscalingPolicy> {
    return this.request<AutoscalingPolicy>("/v1/mesh/load/autoscaling/policy", {
      method: "POST",
      body: JSON.stringify(policy),
    });
  }

  async reportNodeCapacityTelemetry(nodeId: string, metrics: NodeCapacityMetrics): Promise<MeshPeerNode> {
    return this.request<MeshPeerNode>("/v1/mesh/load/heartbeat-telemetry", {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId, metrics }),
    });
  }

  async reapIdleEnclaves(clusterId: string = "cluster-primary"): Promise<AutoscalingEvent[]> {
    return this.request<AutoscalingEvent[]>(`/v1/mesh/load/scale-down/reap?cluster_id=${encodeURIComponent(clusterId)}`, {
      method: "POST",
    });
  }

  // ── Decentralized Vector Sharding & Distributed Raft Consensus (Battery #32 / M117) ──

  async getShardTopology(): Promise<ShardTopologyResponse> {
    return this.request<ShardTopologyResponse>("/v1/shards/topology");
  }

  async queryShardedVectors(query: ScatterGatherQuery): Promise<ScatterGatherResponse> {
    return this.request<ScatterGatherResponse>("/v1/shards/query", {
      method: "POST",
      body: JSON.stringify(query),
    });
  }

  async mutateShardedVectors(mutation: ShardMutationRequest): Promise<ShardMutationResponse> {
    return this.request<ShardMutationResponse>("/v1/shards/mutate", {
      method: "POST",
      body: JSON.stringify(mutation),
    });
  }

  async getRaftConsensusStatus(): Promise<RaftConsensusStatus> {
    return this.request<RaftConsensusStatus>("/v1/shards/raft/status");
  }

  async triggerRaftElection(candidateNodeId: string): Promise<{ success: boolean; current_term: number; active_leader_id: string }> {
    return this.request<{ success: boolean; current_term: number; active_leader_id: string }>("/v1/shards/election", {
      method: "POST",
      body: JSON.stringify({ candidate_node_id: candidateNodeId }),
    });
  }

  async rebalanceShards(payload?: { source_node_id?: string; target_node_id?: string; shard_id?: string }): Promise<ShardRebalancePlan> {
    return this.request<ShardRebalancePlan>("/v1/shards/rebalance", {
      method: "POST",
      body: payload ? JSON.stringify(payload) : undefined,
    });
  }

  async snapshotShard(shardId: string): Promise<Record<string, any>> {
    return this.request<Record<string, any>>(`/v1/shards/${encodeURIComponent(shardId)}/snapshot`, {
      method: "POST",
    });
  }

  // --- Zero-Knowledge Proof (ZKP) Vector Attestation & Grounding (M118) ---

  async getZkpHealth(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>("/v1/zkp/health");
  }

  async computeDocumentMerkleRoot(documentId: string, chunks: Record<string, any>[] = []): Promise<DocumentMerkleRoot> {
    return this.request<DocumentMerkleRoot>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/zkp/merkle-root/${encodeURIComponent(documentId)}`, {
      method: "POST",
      body: JSON.stringify({ chunks }),
    });
  }

  async getChunkInclusionProof(chunkId: string, documentId: string, chunks: Record<string, any>[] = []): Promise<ChunkMerkleProof> {
    return this.request<ChunkMerkleProof>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/zkp/proof/chunk/${encodeURIComponent(chunkId)}`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, chunks }),
    });
  }

  async issueGroundingCertificate(payload: IssueCertificatePayload): Promise<ZkpGroundingCertificate> {
    return this.request<ZkpGroundingCertificate>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/zkp/attest`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async verifyGroundingCertificate(payload: VerifyCertificatePayload): Promise<GroundingVerificationResult> {
    return this.request<GroundingVerificationResult>("/v1/zkp/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async listGroundingCertificates(limit = 50): Promise<ZkpGroundingCertificate[]> {
    return this.request<ZkpGroundingCertificate[]>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/zkp/certificates?limit=${limit}`);
  }

  // --- Enterprise Identity Federation & RB-VAC (M119, Battery #34) ---

  async getSamlConfig(): Promise<SamlIdpConfig> {
    return this.request<SamlIdpConfig>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/saml/config`);
  }

  async configureSamlIdp(config: Partial<SamlIdpConfig>): Promise<SamlIdpConfig> {
    return this.request<SamlIdpConfig>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/saml/config`, {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async getSpMetadataXml(): Promise<string> {
    const res = await fetch(`${this.baseUrl}/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/saml/metadata`, {
      headers: { "X-API-Key": this.apiKey },
    });
    return res.text();
  }

  async validateSamlAcs(samlResponseB64: string): Promise<SamlAssertionPayload> {
    return this.request<SamlAssertionPayload>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/saml/acs`, {
      method: "POST",
      body: JSON.stringify({ saml_response: samlResponseB64 }),
    });
  }

  async generateScimToken(): Promise<{ tenant_id: string; token: string; token_type: string }> {
    return this.request<{ tenant_id: string; token: string; token_type: string }>(
      `/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/scim/token`,
      { method: "POST" }
    );
  }

  async listScimUsers(startIndex = 1, count = 20, filter?: string): Promise<ScimListResponse<ScimUser>> {
    const params = new URLSearchParams({ startIndex: String(startIndex), count: String(count) });
    if (filter) params.set("filter", filter);
    return this.request<ScimListResponse<ScimUser>>(`/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Users?${params.toString()}`);
  }

  async createScimUser(user: Record<string, any>): Promise<ScimUser> {
    return this.request<ScimUser>(`/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Users`, {
      method: "POST",
      body: JSON.stringify(user),
    });
  }

  async patchScimUser(userId: string, operations: any[]): Promise<ScimUser> {
    return this.request<ScimUser>(`/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Users/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      body: JSON.stringify({ Operations: operations }),
    });
  }

  async deleteScimUser(userId: string): Promise<void> {
    await this.request(`/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Users/${encodeURIComponent(userId)}`, {
      method: "DELETE",
    });
  }

  async listScimGroups(startIndex = 1, count = 20): Promise<ScimListResponse<ScimGroup>> {
    return this.request<ScimListResponse<ScimGroup>>(
      `/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Groups?startIndex=${startIndex}&count=${count}`
    );
  }

  async createScimGroup(group: Record<string, any>): Promise<ScimGroup> {
    return this.request<ScimGroup>(`/v1/scim/v2/tenants/${encodeURIComponent(this.tenantId)}/Groups`, {
      method: "POST",
      body: JSON.stringify(group),
    });
  }

  async simulateRbVac(
    userId: string,
    email: string,
    securityGroups: string[],
    candidates: RbVacCandidateChunk[] = []
  ): Promise<RbVacSimulationResult> {
    return this.request<RbVacSimulationResult>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/identity/rbvac/simulate`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, email, security_groups: securityGroups, candidates }),
    });
  }

  // --- Continuous DPO / ORPO Preference Fine-Tuning (M120) ---

  async getTuningConfig(): Promise<ContinuousTuningConfig> {
    return this.request<ContinuousTuningConfig>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/config`);
  }

  async updateTuningConfig(config: Partial<ContinuousTuningConfig>): Promise<ContinuousTuningConfig> {
    return this.request<ContinuousTuningConfig>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/config`, {
      method: "PUT",
      body: JSON.stringify({ ...config, tenant_id: this.tenantId }),
    });
  }

  async listPreferencePairs(limit = 50, offset = 0): Promise<PreferenceListResponse> {
    return this.request<PreferenceListResponse>(
      `/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/pairs?limit=${limit}&offset=${offset}`
    );
  }

  async harvestPreferencePair(pair: {
    prompt: string;
    winning_response: string;
    losing_response: string;
    source_message_id?: string;
    feedback_rating?: number;
    tags?: string[];
  }): Promise<PreferencePair> {
    return this.request<PreferencePair>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/pairs`, {
      method: "POST",
      body: JSON.stringify(pair),
    });
  }

  async deletePreferencePair(pairId: string): Promise<void> {
    await this.request(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/pairs/${encodeURIComponent(pairId)}`, {
      method: "DELETE",
    });
  }

  async triggerTuningJob(
    objective: "dpo" | "orpo" | "kto" = "dpo",
    hyperparams?: Partial<TuningHyperparameters>
  ): Promise<TuningJob> {
    return this.request<TuningJob>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/jobs`, {
      method: "POST",
      body: JSON.stringify({ objective, hyperparameters: hyperparams }),
    });
  }

  async listTuningJobs(limit = 20): Promise<TuningJob[]> {
    return this.request<TuningJob[]>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/jobs?limit=${limit}`);
  }

  async getTuningJob(jobId: string): Promise<TuningJob> {
    return this.request<TuningJob>(`/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/jobs/${encodeURIComponent(jobId)}`);
  }

  async promoteTuningJobAdapter(jobId: string): Promise<ContinuousTuningConfig> {
    return this.request<ContinuousTuningConfig>(
      `/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/jobs/${encodeURIComponent(jobId)}/promote`,
      { method: "POST" }
    );
  }

  async rollbackTuningAdapter(targetAdapterId?: string): Promise<ContinuousTuningConfig> {
    const url = targetAdapterId
      ? `/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/rollback?target_adapter_id=${encodeURIComponent(targetAdapterId)}`
      : `/v1/tenants/${encodeURIComponent(this.tenantId)}/tuning/rollback`;
    return this.request<ContinuousTuningConfig>(url, { method: "POST" });
  }

  async simulateTuningMath(req: {
    prompt: string;
    beta?: number;
    lambda_orpo?: number;
    pi_theta_win_prob?: number;
    pi_ref_win_prob?: number;
    pi_theta_lose_prob?: number;
    pi_ref_lose_prob?: number;
  }): Promise<TuningMathSimulationResult> {
    return this.request<TuningMathSimulationResult>("/v1/tuning/math/simulate", {
      method: "POST",
      body: JSON.stringify(req),
    });
  }
}

export type MeshNodeRole = "seed_gateway" | "sovereign_node" | "edge_enclave" | "remote_peer";
export type MeshNodeStatus = "online" | "degraded" | "standby" | "unreachable";
export type MeshRoutingPolicy = "local_first" | "lowest_latency" | "round_robin" | "failover" | "load_balanced_ewma";
export type FederatedTaskStatus = "pending" | "executing" | "completed" | "failed" | "rejected";

export interface NodeCapacityMetrics {
  cpu_utilization_pct: number;
  memory_utilization_pct: number;
  active_execution_slots: number;
  max_execution_slots: number;
  queue_depth: number;
  ewma_latency_ms: number;
  is_ephemeral: boolean;
  ephemeral_idle_seconds: number;
}

export interface AutoscalingPolicy {
  scale_up_utilization_pct: number;
  scale_up_queue_depth: number;
  scale_up_latency_ms: number;
  scale_down_idle_seconds: number;
  min_enclaves: number;
  max_ephemeral_enclaves: number;
  load_shedding_threshold_pct: number;
}

export interface AutoscalingEvent {
  event_id: string;
  timestamp: number;
  cluster_id: string;
  action: "scale_up" | "scale_down" | "shed_load" | "rebalance";
  reason: string;
  node_id?: string | null;
  trigger_metric: string;
  metric_value: number;
  details?: Record<string, any>;
}

export interface ClusterLoadSummary {
  total_nodes: number;
  online_nodes: number;
  ephemeral_nodes: number;
  clusters: Record<
    string,
    {
      total_nodes: number;
      online_nodes: number;
      ephemeral_nodes: number;
      active_execution_slots: number;
      max_execution_slots: number;
      utilization_pct: number;
      avg_ewma_latency_ms: number;
      queue_depth: number;
      nodes: {
        node_id: string;
        role: string;
        status: string;
        is_ephemeral: boolean;
        active_slots: number;
        max_slots: number;
        cpu_pct: number;
        ewma_latency_ms: number;
        queue_depth: number;
        idle_seconds: number;
      }[];
    }
  >;
}

export interface MeshPeerNode {
  node_id: string;
  cluster_id: string;
  endpoint_url: string;
  role: MeshNodeRole;
  status: MeshNodeStatus;
  advertised_tools: any[];
  latency_ms: number;
  last_heartbeat: number;
  public_key_fingerprint?: string;
  metadata?: Record<string, any>;
  capacity?: NodeCapacityMetrics;
}

export interface MeshStatusSummary {
  battery_id: string;
  status: string;
  total_nodes: number;
  active_nodes: number;
  total_mesh_tools: number;
  routing_policy: MeshRoutingPolicy;
  nodes: MeshPeerNode[];
}

export interface FederatedDelegationResponse {
  delegation_id: string;
  status: FederatedTaskStatus;
  source_cluster_id: string;
  target_cluster_id: string;
  tenant_id: string;
  synthesis: string;
  tool_trace_summary: Record<string, any>[];
  execution_latency_ms: number;
  signature: string;
  error_message?: string | null;
}

// ── Vector Sharding & Raft Consensus Types (Battery #32 / M117) ──────────────

export type ShardStatus = "healthy" | "rebalancing" | "snapshot_sync" | "degraded" | "offline";
export type RaftRole = "leader" | "follower" | "candidate";
export type ReadQuorum = "local" | "one" | "quorum" | "all";
export type WriteQuorum = "one" | "quorum" | "all";

export interface ShardPartition {
  shard_id: string;
  tenant_id?: string | null;
  hash_range_start: number;
  hash_range_end: number;
  leader_node_id: string;
  replica_node_ids: string[];
  status: ShardStatus;
  vector_count: number;
  index_size_bytes: number;
  created_at: number;
  updated_at: number;
}

export interface ShardTopologyResponse {
  cluster_id: string;
  total_shards: number;
  replication_factor: number;
  shards: ShardPartition[];
  skew_metrics: {
    cluster_id?: string;
    node_distribution?: Record<string, number>;
    mean_vectors_per_node?: number;
    skew_std_dev?: number;
    is_skewed?: boolean;
    [key: string]: any;
  };
}

export interface RaftLogEntry {
  index: number;
  term: number;
  command_type: string;
  payload: Record<string, any>;
  timestamp: number;
}

export interface RaftNodeState {
  node_id: string;
  current_term: number;
  voted_for?: string | null;
  role: RaftRole;
  commit_index: number;
  last_applied: number;
  leader_id?: string | null;
  log_length: number;
  heartbeat_timestamp: number;
}

export interface RaftConsensusStatus {
  cluster_id: string;
  current_term: number;
  active_leader_id?: string | null;
  total_nodes: number;
  leader_elected: boolean;
  quorum_healthy: boolean;
  nodes: RaftNodeState[];
  recent_log_entries: RaftLogEntry[];
}

export interface ScatterGatherQuery {
  tenant_id: string;
  query_vector: number[];
  top_k?: number;
  read_quorum?: ReadQuorum;
  filter_metadata?: Record<string, any>;
}

export interface ShardCandidate {
  chunk_id: string;
  score: number;
  text: string;
  metadata: Record<string, any>;
  shard_id: string;
  node_id: string;
}

export interface ShardQueryBreakdown {
  shard_id: string;
  node_id: string;
  latency_ms: number;
  candidates_count: number;
  status: string;
}

export interface ScatterGatherResponse {
  query_id: string;
  tenant_id: string;
  total_shards_queried: number;
  successful_shards: number;
  quorum_achieved: boolean;
  total_latency_ms: number;
  shard_breakdown: ShardQueryBreakdown[];
  results: ShardCandidate[];
}

export interface ShardMutationRequest {
  tenant_id: string;
  document_id: string;
  vectors: {
    chunk_id?: string;
    vector: number[];
    text?: string;
    metadata?: Record<string, any>;
  }[];
  write_quorum?: WriteQuorum;
}

export interface ShardMutationResponse {
  shard_id: string;
  committed_log_index: number;
  term: number;
  vectors_written: number;
  quorum_achieved: boolean;
  elapsed_ms: number;
}

export interface ShardRebalancePlan {
  plan_id: string;
  source_node_id: string;
  target_node_id: string;
  shard_id: string;
  status: string;
  vectors_transferred: number;
  total_vectors: number;
  start_time: number;
  completion_time?: number | null;
  error_message?: string | null;
}

// --- Zero-Knowledge Proof (ZKP) Vector Attestation Types (M118) ---

export interface MerkleProofStep {
  sibling_hash: string;
  direction: "left" | "right";
}

export interface ChunkMerkleProof {
  chunk_id: string;
  chunk_index: number;
  leaf_hash: string;
  merkle_path: MerkleProofStep[];
  document_root: string;
}

export interface ChunkCommitment {
  chunk_id: string;
  chunk_index: number;
  leaf_hash: string;
  merkle_proof: MerkleProofStep[];
  similarity_score?: number;
}

export interface DocumentMerkleRoot {
  document_id: string;
  tenant_id: string;
  root_hash: string;
  chunk_count: number;
  tree_depth: number;
  computed_at: number;
}

export interface ZkpGroundingCertificate {
  certificate_id: string;
  tenant_id: string;
  document_id: string;
  document_merkle_root: string;
  query_hash: string;
  response_hash: string;
  similarity_bound: number;
  chunk_commitments: ChunkCommitment[];
  issued_at: number;
  expires_at?: number | null;
  authority_public_key: string;
  attestation_signature: string;
}

export interface GroundingVerificationResult {
  status:
    | "verified"
    | "root_mismatch"
    | "proof_invalid"
    | "query_mismatch"
    | "response_mismatch"
    | "signature_invalid"
    | "certificate_expired";
  is_valid: boolean;
  details: string;
  verified_at: number;
  checked_leaf_count: number;
  merkle_root_matched: boolean;
  signature_valid: boolean;
  query_match: boolean;
  response_match: boolean;
  execution_time_ms: number;
}

export interface IssueCertificatePayload {
  document_id: string;
  query: string;
  response: string;
  cited_chunks: Record<string, any>[];
  all_document_chunks: Record<string, any>[];
  similarity_bound?: number;
  ttl_seconds?: number;
}

export interface VerifyCertificatePayload {
  certificate: ZkpGroundingCertificate;
  query?: string;
  response?: string;
  expected_document_root?: string;
}

export interface SamlIdpConfig {
  tenant_id: string;
  idp_entity_id: string;
  sso_url: string;
  idp_x509_cert: string;
  sp_entity_id?: string;
  acs_url?: string;
  attribute_mapping?: Record<string, string>;
  default_groups?: string[];
  enabled?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SamlAssertionPayload {
  tenant_id: string;
  name_id: string;
  session_index: string;
  attributes: Record<string, any>;
  security_groups: string[];
  issuer: string;
  issue_instant: string;
  valid_until: string;
  is_verified: boolean;
}

export interface ScimMeta {
  resourceType: string;
  created: string;
  lastModified: string;
  location?: string;
  version?: string;
}

export interface ScimEmail {
  value: string;
  primary?: boolean;
  type?: string;
}

export interface ScimUser {
  schemas?: string[];
  id: string;
  externalId?: string | null;
  userName: string;
  displayName?: string | null;
  active: boolean;
  emails?: ScimEmail[];
  groups?: Array<Record<string, string>>;
  meta?: ScimMeta;
}

export interface ScimGroupMember {
  value: string;
  display?: string | null;
  ref?: string | null;
}

export interface ScimGroup {
  schemas?: string[];
  id: string;
  displayName: string;
  members: ScimGroupMember[];
  meta?: ScimMeta;
}

export interface ScimListResponse<T> {
  schemas: string[];
  totalResults: number;
  startIndex: number;
  itemsPerPage: number;
  Resources: T[];
}

export interface RbVacCandidateChunk {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  acl_groups: string[];
  classification: string;
}

export interface RbVacPrunedTelemetry {
  chunk_id: string;
  document_id: string;
  required_acl_groups: string[];
  user_groups: string[];
  similarity_score: number;
  reason: string;
}

export interface RbVacSimulationResult {
  tenant_id: string;
  user_id: string;
  user_groups: string[];
  total_candidates: number;
  allowed_candidates: RbVacCandidateChunk[];
  pruned_telemetry: RbVacPrunedTelemetry[];
  execution_time_ms: number;
}

// --- Continuous DPO / ORPO Preference Fine-Tuning Types (M120) ---

export type TuningObjective = "dpo" | "orpo" | "kto";
export type TuningJobStatus = "collecting" | "queued" | "training" | "evaluating" | "completed" | "failed" | "rolled_back";

export interface PreferencePair {
  pair_id: string;
  tenant_id: string;
  prompt: string;
  winning_response: string;
  losing_response: string;
  source_message_id?: string | null;
  feedback_rating: number;
  tags: string[];
  is_verified: boolean;
  created_at: string;
}

export interface PreferenceListResponse {
  items: PreferencePair[];
  total: number;
  limit: number;
  offset: number;
}

export interface TuningHyperparameters {
  learning_rate: number;
  beta: number;
  lambda_orpo: number;
  lora_r: number;
  lora_alpha: number;
  batch_size: number;
  epochs: number;
  auto_trigger_threshold: number;
  eval_split_ratio: number;
}

export interface TuningLossStep {
  step: number;
  epoch: number;
  train_loss: number;
  reward_margin: number;
  accuracy: number;
  odds_ratio: number;
}

export interface EvaluationGateResult {
  passed: boolean;
  validation_accuracy: number;
  avg_reward_margin: number;
  validation_loss: number;
  total_eval_pairs: number;
  recommendation: string;
}

export interface ContinuousTuningConfig {
  tenant_id: string;
  objective: TuningObjective;
  base_model: string;
  active_adapter_id?: string | null;
  auto_train_enabled: boolean;
  hyperparameters: TuningHyperparameters;
  total_pairs_harvested: number;
  active_pairs_in_buffer: number;
}

export interface TuningJob {
  job_id: string;
  tenant_id: string;
  objective: TuningObjective;
  status: TuningJobStatus;
  base_model: string;
  output_adapter_id: string;
  dataset_size: number;
  hyperparameters: TuningHyperparameters;
  loss_history: TuningLossStep[];
  evaluation?: EvaluationGateResult | null;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface TuningMathSimulationResult {
  prompt: string;
  beta: number;
  lambda_orpo: number;
  pi_theta_win_prob: number;
  pi_ref_win_prob: number;
  pi_theta_lose_prob: number;
  pi_ref_lose_prob: number;
  dpo_reward_w: number;
  dpo_reward_l: number;
  dpo_reward_margin: number;
  dpo_loss: number;
  orpo_odds_w: number;
  orpo_odds_l: number;
  orpo_odds_ratio: number;
  orpo_loss: number;
}


