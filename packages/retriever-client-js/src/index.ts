export interface RetrieverClientConfig {
  apiKey: string;
  baseUrl: string;
  tenantId: string;
  userId?: string;
}

export interface SearchOptions {
  limit?: number;
  filters?: Record<string, any>;
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

  async search(query: string, options: SearchOptions = {}): Promise<{ results: SearchResultItem[]; searchMeta: { durationMs: number } }> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/search`;
    const body = {
      query,
      limit: options.limit || 5,
    };

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

  async chat(sessionId: string, message: string, options: { xLlmKey?: string } = {}): Promise<any> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages`;
    const headers = this.getHeaders({ "Content-Type": "application/json" });
    if (options.xLlmKey) {
      headers["X-LLM-Key"] = options.xLlmKey;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ query: message, stream: false }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  async *chatStream(sessionId: string, message: string, options: { xLlmKey?: string } = {}): AsyncGenerator<any, void, unknown> {
    const url = `${this.baseUrl}/v1/tenants/${this.tenantId}/chat/sessions/${sessionId}/messages`;
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
      body: JSON.stringify({ query: message, stream: true }),
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
}
