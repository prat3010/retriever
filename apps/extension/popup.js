document.addEventListener("DOMContentLoaded", async () => {
  const pageTitleEl = document.getElementById("page-title");
  const pageUrlEl = document.getElementById("page-url");
  const toggleSettingsBtn = document.getElementById("toggle-settings");
  const settingsDrawerEl = document.getElementById("settings-drawer");
  const serverUrlInput = document.getElementById("server-url");
  const tenantIdInput = document.getElementById("tenant-id");
  const apiKeyInput = document.getElementById("api-key");
  const ingestBtn = document.getElementById("ingest-btn");
  const statusBox = document.getElementById("status-box");

  let currentTab = null;

  // 1. Get active tab
  if (typeof chrome !== "undefined" && chrome.tabs) {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tabs && tabs.length > 0) {
        currentTab = tabs[0];
        pageTitleEl.textContent = currentTab.title || "Active Web Page";
        pageUrlEl.textContent = currentTab.url || "";
      }
    } catch (e) {
      console.error("Error querying tabs:", e);
    }
  }

  // 2. Load stored settings
  if (typeof chrome !== "undefined" && chrome.storage) {
    chrome.storage.local.get(["serverUrl", "tenantId", "apiKey"], (items) => {
      if (items.serverUrl) serverUrlInput.value = items.serverUrl;
      if (items.tenantId) tenantIdInput.value = items.tenantId;
      if (items.apiKey) apiKeyInput.value = items.apiKey;
    });
  }

  // 3. Toggle settings drawer
  toggleSettingsBtn.addEventListener("click", () => {
    settingsDrawerEl.classList.toggle("open");
  });

  // Save settings on input blur
  function saveSettings() {
    if (typeof chrome !== "undefined" && chrome.storage) {
      chrome.storage.local.set({
        serverUrl: serverUrlInput.value.trim(),
        tenantId: tenantIdInput.value.trim(),
        apiKey: apiKeyInput.value.trim(),
      });
    }
  }
  serverUrlInput.addEventListener("blur", saveSettings);
  tenantIdInput.addEventListener("blur", saveSettings);
  apiKeyInput.addEventListener("blur", saveSettings);

  // 4. Ingest button click handler
  ingestBtn.addEventListener("click", async () => {
    saveSettings();

    const serverUrl = (serverUrlInput.value.trim() || "https://rag.prateeq.in").replace(/\/$/, "");
    const tenantId = tenantIdInput.value.trim();
    const apiKey = apiKeyInput.value.trim();

    if (!tenantId) {
      showStatus("Please configure your Tenant ID in workspace settings.", "error");
      settingsDrawerEl.classList.add("open");
      return;
    }

    ingestBtn.disabled = true;
    ingestBtn.textContent = "⏳ Extracting & Indexing...";
    statusBox.style.display = "none";

    try {
      // Extract page content
      let extractedContent = "";
      if (typeof chrome !== "undefined" && chrome.scripting && currentTab) {
        const results = await chrome.scripting.executeScript({
          target: { tabId: currentTab.id },
          func: () => {
            const selection = window.getSelection().toString().trim();
            if (selection) return selection;
            // Strip scripts and styles
            const clone = document.body.cloneNode(true);
            const badTags = clone.querySelectorAll("script, style, noscript, nav, footer, header");
            badTags.forEach((t) => t.remove());
            return clone.innerText.trim();
          },
        });

        if (results && results[0] && results[0].result) {
          extractedContent = results[0].result;
        }
      }

      if (!extractedContent || extractedContent.length < 50) {
        throw new Error("Could not extract readable text content from active tab.");
      }

      const payload = {
        title: currentTab ? currentTab.title : "Web Page Clip",
        content: extractedContent,
        source_url: currentTab ? currentTab.url : null,
        mime_type: "text/markdown",
        tags: ["chrome_extension", "web_clip"],
      };

      const headers = {
        "Content-Type": "application/json",
      };
      if (apiKey) {
        headers["Authorization"] = `Bearer ${apiKey}`;
      }

      const response = await fetch(`${serverUrl}/v1/tenants/${tenantId}/documents/raw`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned HTTP ${response.status}`);
      }

      const resData = await response.json();
      showStatus(
        `✓ Ingested successfully! Indexed ${resData.chunk_count || 1} vector chunks into tenant ${tenantId}.`,
        "success"
      );
    } catch (err) {
      showStatus(`Ingestion failed: ${err.message}`, "error");
    } finally {
      ingestBtn.disabled = false;
      ingestBtn.textContent = "⚡ Ingest Active Page";
    }
  });

  function showStatus(message, type) {
    statusBox.textContent = message;
    statusBox.className = `status-box status-${type}`;
    statusBox.style.display = "block";
  }
});
