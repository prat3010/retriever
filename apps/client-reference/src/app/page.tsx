"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getConfig, saveConfig, clearConfig, RetrieverClient, type RetrieverConfig } from "@/lib/client";

type Tab = "config" | "chat" | "search" | "documents";

export default function Home() {
  const [tab, setTab] = useState<Tab>("config");
  const [config, setConfig] = useState<RetrieverConfig | null>(null);
  const [client, setClient] = useState<RetrieverClient | null>(null);

  useEffect(() => {
    const c = getConfig();
    if (c) {
      setConfig(c);
      setClient(new RetrieverClient(c));
    }
  }, []);

  function handleSaveConfig(c: RetrieverConfig) {
    saveConfig(c);
    setConfig(c);
    setClient(new RetrieverClient(c));
  }

  function handleClear() {
    clearConfig();
    setConfig(null);
    setClient(null);
  }

  return (
    <>
      <aside className="sidebar">
        <h1>Retriever</h1>
        <nav>
          <button className={tab === "config" ? "active" : ""} onClick={() => setTab("config")}>
            Configuration
          </button>
          <button className={tab === "chat" ? "active" : ""} onClick={() => setTab("chat")} disabled={!client}>
            Chat
          </button>
          <button className={tab === "search" ? "active" : ""} onClick={() => setTab("search")} disabled={!client}>
            Search
          </button>
          <button className={tab === "documents" ? "active" : ""} onClick={() => setTab("documents")} disabled={!client}>
            Documents
          </button>
        </nav>
        <div className="badge">Reference Client</div>
      </aside>
      <div className="main">
        <div className="header">
          {client ? `Connected: ${config?.tenantId} (${config?.userId})` : "Not configured"}
        </div>
        <div className="content">
          <ConfigPanel
            key={config?.apiUrl ?? "empty"}
            config={config}
            onSave={handleSaveConfig}
            onClear={handleClear}
            hidden={tab !== "config"}
          />
          <ChatPanel client={client} hidden={tab !== "chat"} />
          <SearchPanel client={client} hidden={tab !== "search"} />
          <DocumentsPanel client={client} hidden={tab !== "documents"} />
        </div>
      </div>
    </>
  );
}

function ConfigPanel({
  config,
  onSave,
  onClear,
  hidden,
}: {
  config: RetrieverConfig | null;
  onSave: (c: RetrieverConfig) => void;
  onClear: () => void;
  hidden: boolean;
}) {
  const [form, setForm] = useState<RetrieverConfig>(
    config ?? { apiUrl: "https://rag.prateeq.in", tenantId: "00000000-0000-0000-0000-000000000000", apiKey: "", userId: "a8b819bb-61bb-450b-9662-62bd06b188d3" },
  );

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  if (hidden) return null;

  return (
    <div className="card">
      <h2>API Configuration</h2>
      <p>Enter your Retriever API credentials from the admin dashboard.</p>
      <label>API Base URL</label>
      <input value={form.apiUrl} onChange={(e) => setForm({ ...form, apiUrl: e.target.value })} placeholder="http://localhost:8000" />
      <div className="row">
        <div>
          <label>Tenant ID</label>
          <input value={form.tenantId} onChange={(e) => setForm({ ...form, tenantId: e.target.value })} placeholder="tn_..." />
        </div>
        <div>
          <label>User ID</label>
          <input value={form.userId} onChange={(e) => setForm({ ...form, userId: e.target.value })} placeholder="00000000-0000-0000-0000-000000000000" />
        </div>
      </div>
      <label>API Key</label>
      <input value={form.apiKey} onChange={(e) => setForm({ ...form, apiKey: e.target.value })} placeholder="sk_..." type="password" />
      <div className="row">
        <div>
          <label>LLM API Key (optional)</label>
          <input value={form.llmKey ?? ""} onChange={(e) => setForm({ ...form, llmKey: e.target.value || undefined })} placeholder="Override tenant LLM key" type="password" />
        </div>
        <div>
          <label>LLM Provider (optional)</label>
          <select value={form.llmProvider ?? ""} onChange={(e) => setForm({ ...form, llmProvider: e.target.value || undefined })} style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)" }}>
            <option value="">Use tenant default</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </div>
      </div>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button className="btn btn-primary" onClick={() => onSave(form)}>
          Save & Connect
        </button>
        {config && (
          <button className="btn btn-danger" onClick={onClear}>
            Disconnect
          </button>
        )}
      </div>
    </div>
  );
}

function ChatPanel({ client, hidden }: { client: RetrieverClient | null; hidden: boolean }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState("");
  const chatEnd = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEnd.current?.scrollIntoView(); }, [messages]);

  async function startSession() {
    if (!client) return;
    try {
      const res = await client.createSession();
      setSessionId(res.sessionId);
      setMessages([{ role: "assistant", content: `Session started: ${res.sessionId}` }]);
      setLog(`POST /chat/sessions → ${JSON.stringify(res)}`);
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
    }
  }

  async function sendMessage() {
    if (!client || !sessionId || !input.trim() || loading) return;
    const msg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const body = await client.chat(sessionId, msg);
      let full = "";
      if (body) {
        const reader = body.getReader();
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          for (const line of text.split("\n")) {
              if (line.startsWith("data: ")) {
                const data = line.slice(6);
                try {
                  const parsed = JSON.parse(data);
                  if (parsed.event === "done") break;
                  full += parsed.content ?? parsed.delta ?? "";
                } catch { /* skip non-JSON SSE */ }
              }
          }
        }
      }
      setMessages((prev) => [...prev, { role: "assistant", content: full || "(empty response)" }]);
      setLog(`POST /chat/sessions/${sessionId}/messages → streamed ${full.length} chars`);
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  if (hidden) return null;

  return (
    <div className="card">
      <h2>Chat</h2>
      <p>Send messages and receive streaming responses.</p>

      <div style={{ marginBottom: "1rem" }}>
        {!sessionId ? (
          <button className="btn btn-primary" onClick={startSession}>Start Session</button>
        ) : (
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Session: {sessionId}
            <button className="btn" style={{ marginLeft: "0.5rem" }} onClick={() => { setSessionId(null); setMessages([]); }}>End</button>
          </span>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>{m.content}</div>
        ))}
        <div ref={chatEnd} />
      </div>

      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type a message..."
          disabled={!sessionId || loading}
        />
        <button className="btn btn-primary" onClick={sendMessage} disabled={!sessionId || loading || !input.trim()}>
          Send
        </button>
      </div>

      {log && <pre className="result" style={{ marginTop: "0.75rem", maxHeight: "80px" }}>{log}</pre>}
    </div>
  );
}

function SearchPanel({ client, hidden }: { client: RetrieverClient | null; hidden: boolean }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState("");

  async function handleSearch() {
    if (!client || !query.trim()) return;
    setLoading(true);
    setLog("");
    try {
      const res = await client.search(query);
      setResults(res);
      setLog(`POST /search → ${res.results.length} results in ${res.searchMeta.durationMs}ms`);
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  if (hidden) return null;

  return (
    <div className="card">
      <h2>Semantic Search</h2>
      <p>Search across indexed documents with hybrid retrieval.</p>

      <div className="chat-input">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search query..."
        />
        <button className="btn btn-primary" onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {results && (
        <div style={{ marginTop: "1rem" }}>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Found {results.results.length} results
          </p>
          {results.results.map((r: any, i: number) => (
            <div key={r.chunkId} style={{ padding: "0.75rem", borderBottom: "1px solid var(--border)", fontSize: "0.875rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                <span style={{ fontWeight: 500 }}>#{i + 1}</span>
                <span style={{ color: "var(--text-muted)" }}>Score: {r.score.toFixed(4)}</span>
              </div>
              <p>{r.content}</p>
            </div>
          ))}
        </div>
      )}

      {log && <pre className="result" style={{ marginTop: "0.75rem", maxHeight: "80px" }}>{log}</pre>}
    </div>
  );
}

function DocumentsPanel({ client, hidden }: { client: RetrieverClient | null; hidden: boolean }) {
  const [docs, setDocs] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [log, setLog] = useState("");

  const fetchDocs = useCallback(async () => {
    if (!client) return;
    setLoading(true);
    try {
      const res = await client.listDocuments();
      setDocs(res as any[]);
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [client]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !client) return;
    setUploading(true);
    try {
      const res = await client.uploadDocument(file);
      setLog(`POST /documents → ${JSON.stringify(res)}`);
      await fetchDocs();
    } catch (e: any) {
      setLog(`Error: ${e.message}`);
    } finally {
      setUploading(false);
    }
  }

  if (hidden) return null;

  return (
    <div className="card">
      <h2>Documents</h2>
      <p>Upload and manage documents for indexing.</p>

      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <button className="btn btn-primary" onClick={fetchDocs} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>
        <label className="btn" style={{ cursor: "pointer" }}>
          {uploading ? "Uploading..." : "Upload Document"}
          <input type="file" style={{ display: "none" }} onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {docs && docs.length === 0 && <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>No documents yet.</p>}

      {docs && docs.length > 0 && (
        <ul className="file-list">
          {docs.map((doc: any) => (
            <li key={doc.documentId}>
              <span>{doc.filename}</span>
              <span style={{ color: "var(--text-muted)" }}>{doc.status}</span>
            </li>
          ))}
        </ul>
      )}

      {log && <pre className="result" style={{ marginTop: "0.75rem", maxHeight: "80px" }}>{log}</pre>}
    </div>
  );
}
