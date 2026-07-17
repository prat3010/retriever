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
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${this.config.apiKey}`,
      "X-User-ID": this.config.userId,
    };
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(url, {
      ...options,
      headers: { ...headers, ...(options.headers as Record<string, string>) },
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
        "Authorization": `Bearer ${this.config.apiKey}`,
        "X-User-ID": this.config.userId,
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ query: message }),
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
        "Authorization": `Bearer ${this.config.apiKey}`,
        "X-User-ID": this.config.userId,
      },
      body: formData,
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  }
}
