"use client";

import { useState, useEffect } from "react";
import { getConfig, saveConfig, clearConfig, RetrieverClient, type RetrieverConfig } from "@/lib/client";

export default function Home() {
  const [config, setConfig] = useState<RetrieverConfig | null>(null);
  const [client, setClient] = useState<RetrieverClient | null>(null);

  useEffect(() => {
    const c = getConfig();
    if (c) {
      setConfig(c);
      setClient(new RetrieverClient(c));
    }
  }, []);

  function handleSave(c: RetrieverConfig) {
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
    <main className="container">
      <h1>Retriever API Reference</h1>
      <p className="subtitle">Curl examples for every Retriever endpoint. <a href="https://rag.prateeq.in/docs">Full API docs →</a></p>

      <section>
        <h2>Configuration</h2>
        <div className="config-row">
          <input value={config?.apiUrl ?? ""} placeholder="API URL" onChange={() => {}} readOnly />
          <input value={config?.apiKey ?? ""} placeholder="API Key" type="password" onChange={() => {}} readOnly />
          <button className="btn" onClick={() => {
            const url = prompt("API Base URL", "https://rag.prateeq.in");
            const key = prompt("API Key");
            const tenant = prompt("Tenant ID", "00000000-0000-0000-0000-000000000000");
            const user = prompt("User ID", "a8b819bb-61bb-450b-9662-62bd06b188d3");
            if (url && key && tenant && user) {
              handleSave({ apiUrl: url, tenantId: tenant, apiKey: key, userId: user });
            }
          }}>
            {client ? "Update" : "Connect"}
          </button>
          {client && <button className="btn danger" onClick={handleClear}>Disconnect</button>}
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
