"use client";

import { useState, useEffect, useRef } from "react";
import { RetrieverClient, DocumentResponse, SearchResultItem } from "@prat3010/retriever-client-js";
import styles from "./components.module.css";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: SearchResultItem[];
}

export default function DeveloperConsole() {
  // Settings State
  const [baseUrl, setBaseUrl] = useState("http://localhost:8000");
  const [tenantId, setTenantId] = useState("00000000-0000-0000-0000-000000000000");
  const [apiKey, setApiKey] = useState("dev-admin-master-key-change-in-production");
  const [activeModel, setActiveModel] = useState("gemini-1.5-flash");
  const [llmApiKey, setLlmApiKey] = useState("");
  
  // Validation State
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; error?: string } | null>(null);

  // Documents & Sync State
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // Chat State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Citation Modal State
  const [activeCitation, setActiveCitation] = useState<SearchResultItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize Client SDK
  const getClient = () => {
    return new RetrieverClient({
      apiKey,
      baseUrl,
      tenantId,
    });
  };

  // Scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch Documents List
  const fetchDocuments = async () => {
    setDocumentsLoading(true);
    try {
      const client = getClient();
      const res = await client.listDocuments({ limit: 100 });
      if (Array.isArray(res)) {
        setDocuments(res);
      } else if (res && Array.isArray(res.items)) {
        setDocuments(res.items);
      }
    } catch (e) {
      console.error("Failed to fetch documents:", e);
    } finally {
      setDocumentsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [tenantId, baseUrl, apiKey]);

  // Validate API Key
  const handleValidateKey = async () => {
    setValidationLoading(true);
    setValidationResult(null);
    try {
      // Direct call to validation endpoint with Admin headers
      const response = await fetch(`${baseUrl}/v1/config/validate-key`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
          "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          api_key: llmApiKey,
          base_url: activeModel === "gemini-1.5-flash" ? "https://generativelanguage.googleapis.com/v1beta/openai/" : "",
          provider: activeModel === "gemini-1.5-flash" ? "gemini" : "openai",
          model: activeModel
        })
      });
      const data = await response.json();
      if (response.ok) {
        setValidationResult({ valid: data.valid, error: data.error });
      } else {
        setValidationResult({ valid: false, error: data.detail || "Connection request failed" });
      }
    } catch (e: any) {
      setValidationResult({ valid: false, error: e.message || "Failed to reach backend server" });
    } finally {
      setValidationLoading(false);
    }
  };

  // Re-run Codebase Ingestion
  const handleTriggerSync = async () => {
    setIsSyncing(true);
    try {
      const response = await fetch(`${baseUrl}/v1/admin/tenants/${tenantId}/reindex`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Master-Key": apiKey,
          "Authorization": `Bearer ${apiKey}`
        }
      });
      if (response.ok) {
        alert("Codebase synchronization triggered successfully!");
        setTimeout(fetchDocuments, 2000);
      } else {
        const errData = await response.json().catch(() => ({ detail: "Unknown error" }));
        alert(`Failed to trigger sync: ${errData.detail || "Request failed"}`);
      }
    } catch (e: any) {
      console.error(e);
      alert(`Failed to connect to backend: ${e.message || e}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Send Chat Message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || chatLoading) return;

    const userText = inputMessage;
    setInputMessage("");
    setChatLoading(true);

    // Append user message immediately
    setMessages(prev => [...prev, { role: "user", content: userText }]);

    try {
      const client = getClient();
      let currentSessionId = sessionId;

      // Create session if it doesn't exist yet
      if (!currentSessionId) {
        const sessionRes = await client.createSession();
        currentSessionId = sessionRes.sessionId;
        setSessionId(currentSessionId);
      }

      // 1. Fetch matching search chunks in parallel to support code citations view
      const searchRes = await client.search(userText, { limit: 5 });
      const matchingChunks = searchRes.results || [];

      // 2. Append assistant response placeholder
      setMessages(prev => [...prev, { role: "assistant", content: "", citations: matchingChunks }]);

      // 3. Start streaming chat tokens
      let streamedResponse = "";
      const chatOptions: any = {};
      if (llmApiKey) {
        chatOptions.xLlmKey = llmApiKey;
      }
      const stream = client.chatStream(currentSessionId, userText, chatOptions);

      for await (const chunk of stream) {
        if (chunk && chunk.event === "token") {
          const delta = chunk.delta || "";
          streamedResponse += delta;
          
          // Update last assistant message content in real time
          setMessages(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              last.content = streamedResponse;
            }
            return updated;
          });
        }
      }
    } catch (e: any) {
      console.error("Chat streaming failed:", e);
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: `Error: ${e.message || "Failed to fetch response."}` }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Format response content to render citation markers as buttons
  const renderMessageContent = (msg: Message) => {
    if (msg.role === "user") return msg.content;

    // Split text to find citation markers like [1], [2]
    const parts = msg.content.split(/(\[\d+\])/g);
    
    return (
      <>
        {parts.map((part, i) => {
          const match = part.match(/\[(\d+)\]/);
          if (match && msg.citations) {
            const index = parseInt(match[1]) - 1;
            const citation = msg.citations[index];
            if (citation) {
              const meta = citation.metadata || {};
              const filename = meta.file_path || meta.filename || "Source";
              
              return (
                <button
                  key={i}
                  className={styles.citationBtn}
                  onClick={() => setActiveCitation(citation)}
                  title={filename}
                >
                  [{match[1]}] {filename.split("/").pop()}
                </button>
              );
            }
          }
          return part;
        })}
      </>
    );
  };

  return (
    <div className={styles.container}>
      {/* Sidebar Panel */}
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <span>⚡</span>
            <span>Retriever DevConsole</span>
          </div>
        </div>
        <div className={styles.sidebarScroll}>
          <h4 className={styles.sectionTitle}>Workspace Documents</h4>
          {documentsLoading ? (
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Loading documents...</p>
          ) : (
            <div className={styles.docList}>
              {documents.map(doc => (
                <div key={doc.documentId} className={styles.docItem}>
                  <span className={styles.docName} title={doc.filename}>
                    {doc.filename}
                  </span>
                  <span className={styles.docMeta}>
                    {doc.status}
                  </span>
                </div>
              ))}
              {documents.length === 0 && (
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>No documents indexed yet.</p>
              )}
            </div>
          )}
        </div>
        <div className={styles.sidebarFooter}>
          <button 
            className={styles.syncBtn} 
            onClick={handleTriggerSync}
            disabled={isSyncing}
          >
            🔄 {isSyncing ? "Syncing Codebase..." : "Sync Local Files"}
          </button>
        </div>
      </div>

      {/* Chat Pane */}
      <div className={styles.chatPane}>
        <div className={styles.chatHeader}>
          <span className={styles.chatTitle}>Self-Aware Copilot Chat</span>
          <span style={{ fontSize: "0.8rem", display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="connected-dot"></span>
            Ollama (Local Embeddings)
          </span>
        </div>
        <div className={styles.chatMessages}>
          {messages.map((msg, i) => (
            <div 
              key={i} 
              className={`${styles.messageRow} ${
                msg.role === "user" ? styles.userMessage : styles.assistantMessage
              }`}
            >
              {renderMessageContent(msg)}
            </div>
          ))}
          {chatLoading && (
            <div className={`${styles.messageRow} ${styles.assistantMessage}`} style={{ opacity: 0.6 }}>
              Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className={styles.chatFooter}>
          <form className={styles.chatForm} onSubmit={handleSendMessage}>
            <input
              type="text"
              className={styles.chatInput}
              placeholder="Ask a question about connection pool, RLS rules, celery configurations..."
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              disabled={chatLoading}
            />
            <button className={styles.sendBtn} type="submit" disabled={chatLoading}>
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Settings Panel */}
      <div className={styles.settings}>
        <div className={styles.settingsSection}>
          <h4 className={styles.settingsLabel}>Settings</h4>
          
          <div className={styles.inputGroup}>
            <span className={styles.inputLabel}>FastAPI Base URL</span>
            <input
              type="text"
              className={styles.textInput}
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
            />
          </div>

          <div className={styles.inputGroup}>
            <span className={styles.inputLabel}>Tenant UUID</span>
            <input
              type="text"
              className={styles.textInput}
              value={tenantId}
              onChange={e => setTenantId(e.target.value)}
            />
          </div>

          <div className={styles.inputGroup}>
            <span className={styles.inputLabel}>Admin Master Key</span>
            <input
              type="password"
              className={styles.textInput}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.settingsSection} style={{ borderTop: "1px solid var(--card-border)", paddingTop: "20px" }}>
          <h4 className={styles.settingsLabel}>Cognitive Key Validation</h4>
          
          <div className={styles.inputGroup}>
            <span className={styles.inputLabel}>Active LLM Model</span>
            <select 
              className={styles.textInput}
              value={activeModel}
              onChange={e => setActiveModel(e.target.value)}
            >
              <option value="gemini-1.5-flash">gemini-1.5-flash</option>
              <option value="gpt-4o">gpt-4o</option>
            </select>
          </div>

          <div className={styles.inputGroup}>
            <span className={styles.inputLabel}>Provider API Key (Optional)</span>
            <input
              type="password"
              className={styles.textInput}
              value={llmApiKey}
              onChange={e => setLlmApiKey(e.target.value)}
              placeholder="Defaults to server .env key"
            />
          </div>

          <button 
            className={styles.validateBtn}
            onClick={handleValidateKey}
            disabled={validationLoading}
          >
            {validationLoading ? "Testing..." : "Test Provider Connection"}
          </button>

          {validationResult && (
            <div className={`${styles.validationResult} ${
              validationResult.valid ? styles.validResult : styles.invalidResult
            }`}>
              {validationResult.valid ? (
                <span>🟢 Connection Successful! Key is valid.</span>
              ) : (
                <span>🔴 Validation Failed: {validationResult.error}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Citation Source Popup Modal */}
      {activeCitation && (
        <div className={styles.modalOverlay} onClick={() => setActiveCitation(null)}>
          <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>
                📄 {activeCitation.metadata?.file_path || activeCitation.metadata?.filename || "Source Chunk"}
              </span>
              <button className={styles.closeBtn} onClick={() => setActiveCitation(null)}>
                &times;
              </button>
            </div>
            <div className={styles.modalBody}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
                <span>Relevance Score: {activeCitation.score.toFixed(4)}</span>
                {activeCitation.metadata?.ast_node_type && (
                  <span style={{ marginLeft: "12px" }}>Node Type: {activeCitation.metadata.ast_node_type}</span>
                )}
              </div>
              <pre className={styles.codeSnippet}>
                <code>{activeCitation.content}</code>
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
