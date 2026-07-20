"use client";

import { useState, useEffect } from "react";
import { getConfig, saveConfig, clearConfig, RetrieverClient, type RetrieverConfig } from "@/lib/client";

const LLM_PROVIDERS = [
  { value: "", label: "Default (tenant config)" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "openai", label: "OpenAI" },
  { value: "google-ai-studio", label: "Gemini" },
  { value: "anthropic", label: "Anthropic" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "groq", label: "Groq" },
  { value: "mistral", label: "Mistral" },
  { value: "xai", label: "xAI" },
  { value: "together", label: "Together" },
  { value: "fireworks", label: "Fireworks" },
  { value: "perplexity", label: "Perplexity" },
];

export default function Home() {
  const [config, setConfig] = useState<RetrieverConfig | null>(null);
  const [client, setClient] = useState<RetrieverClient | null>(null);
  const [form, setForm] = useState({ apiUrl: "https://rag.prateeq.in", tenantId: "", apiKey: "", userId: "", llmKey: "", llmProvider: "" });

  useEffect(() => {
    const c = getConfig();
    if (c) {
      setConfig(c);
      setClient(new RetrieverClient(c));
      setForm({ apiUrl: c.apiUrl, tenantId: c.tenantId, apiKey: c.apiKey, userId: c.userId, llmKey: c.llmKey ?? "", llmProvider: c.llmProvider ?? "" });
    }
  }, []);

  function handleConnect() {
    if (!form.apiUrl || !form.tenantId || !form.apiKey || !form.userId) return;
    const cfg: RetrieverConfig = {
      apiUrl: form.apiUrl,
      tenantId: form.tenantId,
      apiKey: form.apiKey,
      userId: form.userId,
    };
    if (form.llmKey) cfg.llmKey = form.llmKey;
    if (form.llmProvider) cfg.llmProvider = form.llmProvider;
    saveConfig(cfg);
    setConfig(cfg);
    setClient(new RetrieverClient(cfg));
  }

  function handleClear() {
    clearConfig();
    setConfig(null);
    setClient(null);
    setForm({ apiUrl: "https://rag.prateeq.in", tenantId: "", apiKey: "", userId: "", llmKey: "", llmProvider: "" });
  }

  return (
    <main className="container">
      <h1>Retriever API Reference</h1>
      <p className="subtitle">Curl examples for every Retriever endpoint. <a href="https://rag.prateeq.in/docs">Full API docs →</a></p>

      <section>
        <h2>Configuration</h2>
        <div className="config-form">
          <div className="row">
            <div className="field">
              <label>API URL</label>
              <input value={form.apiUrl} onChange={(e) => setForm({ ...form, apiUrl: e.target.value })} placeholder="https://rag.prateeq.in" />
            </div>
            <div className="field">
              <label>API Key</label>
              <input value={form.apiKey} onChange={(e) => setForm({ ...form, apiKey: e.target.value })} type="password" placeholder="sk-..." />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>Tenant ID</label>
              <input value={form.tenantId} onChange={(e) => setForm({ ...form, tenantId: e.target.value })} placeholder="00000000-0000-0000-0000-000000000000" />
            </div>
            <div className="field">
              <label>User ID</label>
              <input value={form.userId} onChange={(e) => setForm({ ...form, userId: e.target.value })} placeholder="a8b819bb-61bb-450b-9662-62bd06b188d3" />
            </div>
          </div>
          <div className="row">
            <div className="field">
              <label>LLM Provider <span style={{color:'var(--text-muted)'}}>(optional)</span></label>
              <select value={form.llmProvider} onChange={(e) => setForm({ ...form, llmProvider: e.target.value })}>
                {LLM_PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>LLM Key <span style={{color:'var(--text-muted)'}}>(optional)</span></label>
              <input value={form.llmKey} onChange={(e) => setForm({ ...form, llmKey: e.target.value })} type="password" placeholder="Override tenant LLM key" />
            </div>
          </div>
          <div className="actions">
            <button className="btn primary" onClick={handleConnect}>{client ? "Update" : "Connect"}</button>
            {client && <button className="btn danger" onClick={handleClear}>Disconnect</button>}
          </div>
        </div>
        {client && <p className="status">Connected: {config?.tenantId} ({config?.userId})</p>}
      </section>

      {client && (
        <>
          <section>
            <h2>Search</h2>
            <pre className="code-block">{`curl -X POST ${config?.apiUrl}/v1/tenants/${config?.tenantId}/search \\
  -H "Authorization: Bearer ${config?.apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "your search query", "top_k": 5}'`}</pre>
          </section>

          <section>
            <h2>Chat — Create Session</h2>
            <pre className="code-block">{`curl -X POST ${config?.apiUrl}/v1/tenants/${config?.tenantId}/chat/sessions \\
  -H "Authorization: Bearer ${config?.apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "${config?.userId}"}'`}</pre>
          </section>

          <section>
            <h2>Chat — Send Message (SSE stream)</h2>
            <pre className="code-block">{`curl -X POST ${config?.apiUrl}/v1/tenants/${config?.tenantId}/chat/sessions/{sessionId}/messages \\
  -H "Authorization: Bearer ${config?.apiKey}" \\
  -H "X-User-ID: ${config?.userId}" \\
  -H "Accept: text/event-stream" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Your question here"}'`}</pre>
          </section>

          <section>
            <h2>Documents — List</h2>
            <pre className="code-block">{`curl ${config?.apiUrl}/v1/tenants/${config?.tenantId}/documents \\
  -H "Authorization: Bearer ${config?.apiKey}" \\
  -H "X-User-ID: ${config?.userId}"`}</pre>
          </section>

          <section>
            <h2>Documents — Upload</h2>
            <pre className="code-block">{`curl -X POST ${config?.apiUrl}/v1/tenants/${config?.tenantId}/documents \\
  -H "Authorization: Bearer ${config?.apiKey}" \\
  -H "X-User-ID: ${config?.userId}" \\
  -F "file=@/path/to/document.pdf"`}</pre>
          </section>
        </>
      )}

      <footer>
        <p>Built with the <a href="https://github.com/anomalyco/retriever">Retriever engine</a>. For a full interactive UI, visit the <a href="https://prateeq.in/rag">branded RAG interface →</a></p>
      </footer>
    </main>
  );
}
