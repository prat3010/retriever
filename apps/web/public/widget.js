/**
 * Retriever AI Embeddable Chat Widget v1.0.0
 * Lightweight, zero-dependency embeddable chat client.
 * 
 * Usage:
 * <script 
 *   src="https://admin.rag.prateeq.in/widget.js" 
 *   data-tenant="YOUR_TENANT_ID" 
 *   data-key="YOUR_API_KEY" 
 *   data-color="#2563eb" 
 *   data-title="Retriever Concierge" 
 *   data-position="bottom-right"
 *   data-api-url="https://rag.prateeq.in">
 * </script>
 */
(function () {
  "use strict";

  // Identify config from current script tag
  const script = document.currentScript || (function() {
    const scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  const tenantId = script?.getAttribute("data-tenant") || "";
  const apiKey = script?.getAttribute("data-key") || "";
  const brandColor = script?.getAttribute("data-color") || "#2563eb";
  const botTitle = script?.getAttribute("data-title") || "Retriever AI";
  const position = script?.getAttribute("data-position") || "bottom-right";
  const apiUrl = (script?.getAttribute("data-api-url") || "https://rag.prateeq.in").replace(/\/$/, "");
  const containerId = script?.getAttribute("data-container") || "";

  let sessionId = "";
  let isOpen = false;
  let isStreaming = false;

  // Generate or retrieve persistent user UUID
  let userId = localStorage.getItem("retriever_widget_uid");
  if (!userId) {
    userId = "wgt_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
    localStorage.setItem("retriever_widget_uid", userId);
  }

  // Inject Styles
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    .retriever-widget-launcher {
      position: fixed;
      ${position.includes("left") ? "left: 20px;" : "right: 20px;"}
      bottom: 20px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: ${brandColor};
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
      border: 2px solid rgba(255,255,255,0.2);
    }
    .retriever-widget-launcher:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(0,0,0,0.35);
    }
    .retriever-widget-launcher svg {
      width: 28px;
      height: 28px;
      fill: #ffffff;
      transition: transform 0.2s ease;
    }
    .retriever-widget-panel {
      position: fixed;
      ${position.includes("left") ? "left: 20px;" : "right: 20px;"}
      bottom: 88px;
      width: 380px;
      max-width: calc(100vw - 40px);
      height: 560px;
      max-height: calc(100vh - 110px);
      background: #0f172a;
      color: #f8fafc;
      border-radius: 16px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.45);
      border: 1px solid rgba(255,255,255,0.1);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      opacity: 0;
      transform: translateY(12px) scale(0.96);
      pointer-events: none;
      transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .retriever-widget-panel.retriever-open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: all;
    }
    .retriever-widget-inline {
      width: 100%;
      height: 100%;
      min-height: 420px;
      position: relative;
      bottom: auto;
      right: auto;
      left: auto;
      box-shadow: none;
      opacity: 1;
      transform: none;
      pointer-events: all;
    }
    .retriever-header {
      padding: 14px 18px;
      background: #1e293b;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .retriever-header-title {
      font-weight: 600;
      font-size: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .retriever-status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    .retriever-close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
      padding: 4px;
      border-radius: 6px;
    }
    .retriever-close-btn:hover {
      color: #f8fafc;
      background: rgba(255,255,255,0.08);
    }
    .retriever-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      font-size: 13.5px;
      line-height: 1.5;
    }
    .retriever-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      word-break: break-word;
    }
    .retriever-msg-bot {
      align-self: flex-start;
      background: #1e293b;
      color: #e2e8f0;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(255,255,255,0.05);
    }
    .retriever-msg-user {
      align-self: flex-end;
      background: ${brandColor};
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .retriever-footer {
      padding: 12px 14px;
      background: #1e293b;
      border-top: 1px solid rgba(255,255,255,0.08);
      display: flex;
      gap: 8px;
    }
    .retriever-input {
      flex: 1;
      background: #0f172a;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 8px;
      padding: 9px 12px;
      color: #f8fafc;
      font-size: 13.5px;
      outline: none;
      transition: border-color 0.15s ease;
    }
    .retriever-input:focus {
      border-color: ${brandColor};
    }
    .retriever-send-btn {
      background: ${brandColor};
      border: none;
      border-radius: 8px;
      padding: 0 14px;
      color: #ffffff;
      font-weight: 600;
      cursor: pointer;
      font-size: 13px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.15s ease;
    }
    .retriever-send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .retriever-branding {
      text-align: center;
      font-size: 10px;
      color: #64748b;
      padding-bottom: 6px;
      background: #1e293b;
    }
    .retriever-branding a {
      color: #94a3b8;
      text-decoration: none;
    }
  `;
  document.head.appendChild(styleEl);

  // Render Widget DOM
  const panel = document.createElement("div");
  panel.className = "retriever-widget-panel" + (containerId ? " retriever-widget-inline retriever-open" : "");
  panel.innerHTML = `
    <div class="retriever-header">
      <div class="retriever-header-title">
        <span class="retriever-status-dot"></span>
        <span>${botTitle}</span>
      </div>
      ${!containerId ? `<button class="retriever-close-btn" aria-label="Close chat">×</button>` : ""}
    </div>
    <div class="retriever-messages" id="retriever-msg-list">
      <div class="retriever-msg retriever-msg-bot">
        👋 Hi! How can I help you scope your project or answer questions today?
      </div>
    </div>
    <div class="retriever-footer">
      <input type="text" class="retriever-input" placeholder="Type a message..." aria-label="Message" />
      <button class="retriever-send-btn">Send</button>
    </div>
    <div class="retriever-branding">
      ⚡ Powered by <a href="https://prateeq.in/rag" target="_blank" rel="noopener">Retriever RAG</a>
    </div>
  `;

  if (containerId) {
    const container = document.getElementById(containerId);
    if (container) container.appendChild(panel);
    else document.body.appendChild(panel);
  } else {
    document.body.appendChild(panel);
    
    // Create floating launcher button
    const launcher = document.createElement("div");
    launcher.className = "retriever-widget-launcher";
    launcher.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
      </svg>
    `;
    document.body.appendChild(launcher);

    launcher.addEventListener("click", () => {
      isOpen = !isOpen;
      if (isOpen) {
        panel.classList.add("retriever-open");
        panel.querySelector("input")?.focus();
      } else {
        panel.classList.remove("retriever-open");
      }
    });

    panel.querySelector(".retriever-close-btn")?.addEventListener("click", () => {
      isOpen = false;
      panel.classList.remove("retriever-open");
    });
  }

  const msgList = panel.querySelector("#retriever-msg-list");
  const inputEl = panel.querySelector(".retriever-input");
  const sendBtn = panel.querySelector(".retriever-send-btn");

  async function ensureSession() {
    if (sessionId) return sessionId;
    try {
      const res = await fetch(`${apiUrl}/v1/tenants/${tenantId}/chat/sessions`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "X-API-Key": apiKey,
          "X-User-ID": userId,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ user_id: userId })
      });
      if (res.ok) {
        const data = await res.json();
        sessionId = data.sessionId || data.session_id || "";
      }
    } catch (e) {
      console.warn("Retriever widget session init fallback:", e);
    }
    return sessionId;
  }

  async function handleSend() {
    const text = inputEl.value.trim();
    if (!text || isStreaming) return;

    inputEl.value = "";
    sendBtn.disabled = true;
    isStreaming = true;

    // Add User Message
    const userMsg = document.createElement("div");
    userMsg.className = "retriever-msg retriever-msg-user";
    userMsg.textContent = text;
    msgList.appendChild(userMsg);
    msgList.scrollTop = msgList.scrollHeight;

    // Add Bot Placeholder
    const botMsg = document.createElement("div");
    botMsg.className = "retriever-msg retriever-msg-bot";
    botMsg.textContent = "...";
    msgList.appendChild(botMsg);
    msgList.scrollTop = msgList.scrollHeight;

    try {
      await ensureSession();
      const endpoint = sessionId 
        ? `${apiUrl}/v1/tenants/${tenantId}/chat/sessions/${sessionId}/messages`
        : `${apiUrl}/v1/tenants/${tenantId}/chat`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "X-API-Key": apiKey,
          "X-User-ID": userId,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: text,
          stream: true,
          web_search_grounding: true
        })
      });

      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }

      if (res.body && res.headers.get("content-type")?.includes("text/event-stream")) {
        botMsg.textContent = "";
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data:")) {
              const dataStr = trimmed.slice(5).trim();
              if (dataStr === "[DONE]") break;
              try {
                const parsed = JSON.parse(dataStr);
                const token = parsed.token || parsed.content || parsed.text || "";
                botMsg.textContent += token;
                msgList.scrollTop = msgList.scrollHeight;
              } catch {
                if (dataStr && !dataStr.startsWith("{")) {
                  botMsg.textContent += dataStr;
                }
              }
            }
          }
        }
      } else {
        const data = await res.json();
        botMsg.textContent = data.response || data.content || data.answer || "No response received.";
      }
    } catch (err) {
      botMsg.textContent = "⚠️ Sorry, I encountered an issue connecting to the knowledge base.";
      console.error("Retriever widget error:", err);
    } finally {
      isStreaming = false;
      sendBtn.disabled = false;
      msgList.scrollTop = msgList.scrollHeight;
    }
  }

  sendBtn.addEventListener("click", handleSend);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSend();
  });
})();
