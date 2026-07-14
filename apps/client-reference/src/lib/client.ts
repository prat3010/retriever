export interface RetrieverConfig {
  apiUrl: string;
  tenantId: string;
  apiKey: string;
  userId: string;
}

const STORAGE_KEY = "retriever_config";

export function getConfig(): RetrieverConfig | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function saveConfig(config: RetrieverConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function clearConfig() {
  localStorage.removeItem(STORAGE_KEY);
}

export class RetrieverClient {
  private config: RetrieverConfig;

  constructor(config: RetrieverConfig) {
    this.config = config;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.config.apiUrl.replace(/\/$/, "")}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": this.config.apiKey,
        "X-User-ID": this.config.userId,
        ...options.headers,
      },
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  }

  async listDocuments() {
    return this.request<unknown[]>(`/v1/tenants/${this.config.tenantId}/documents`);
  }

  async search(query: string, limit = 5) {
    return this.request<{ results: Array<{ chunkId: string; content: string; score: number }>; searchMeta: { durationMs: number } }>(
      `/v1/tenants/${this.config.tenantId}/search`,
      { method: "POST", body: JSON.stringify({ query, limit }) },
    );
  }

  async chat(sessionId: string, message: string): Promise<ReadableStream<Uint8Array> | null> {
    const url = `${this.config.apiUrl.replace(/\/$/, "")}/v1/tenants/${this.config.tenantId}/chat/sessions/${sessionId}/messages`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": this.config.apiKey,
        "X-User-ID": this.config.userId,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.body;
  }

  async createSession() {
    return this.request<{ sessionId: string }>(
      `/v1/tenants/${this.config.tenantId}/chat/sessions`,
      { method: "POST" },
    );
  }

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const url = `${this.config.apiUrl.replace(/\/$/, "")}/v1/tenants/${this.config.tenantId}/documents`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-API-Key": this.config.apiKey,
        "X-User-ID": this.config.userId,
      },
      body: formData,
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  }
}
