"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Send, Loader2, Terminal } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function TenantSandboxTab({ tenantId }: { tenantId: string }) {
  const [apiKey, setApiKey] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);

  useEffect(() => { chatEnd.current?.scrollIntoView(); }, [messages]);

  async function startSession() {
    if (!apiKey.trim()) { toast.error("Enter a tenant API key first"); return; }
    try {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/chat/sessions`, {
        method: "POST",
        headers: { "X-API-Key": apiKey.trim(), "X-User-ID": "admin_demo", "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSessionId(data.sessionId);
      setMessages([{ role: "assistant", content: `Session started: ${data.sessionId}` }]);
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  async function sendMessage() {
    if (!sessionId || !input.trim() || loading) return;
    const msg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: {
          "X-API-Key": apiKey.trim(),
          "X-User-ID": "admin_demo",
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ query: msg, stream: true }),
      });
      if (!res.ok) throw new Error(await res.text());

      let full = "";
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          for (const line of text.split("\n")) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              if (data === "[DONE]") break;
              try {
                const parsed = JSON.parse(data);
                if (parsed.delta) full += parsed.delta;
                else if (parsed.content) full += parsed.content;
              } catch { /* skip non-JSON SSE */ }
            }
          }
        }
      }
      setMessages((prev) => [...prev, { role: "assistant", content: full || "(empty)" }]);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Terminal className="h-4 w-4" /> RAG Sandbox
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!sessionId && (
            <div className="space-y-2">
              <Label>Tenant API Key</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="sk_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="flex-1"
                />
                <Button onClick={startSession}>Start Session</Button>
              </div>
            </div>
          )}

          {sessionId && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Session: {sessionId.slice(0, 8)}...</span>
                <Button variant="outline" size="sm" onClick={startSession}>New Session</Button>
              </div>

              <div className="rounded-lg border bg-muted/30 p-4 max-h-64 overflow-y-auto space-y-2">
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`rounded-lg px-3 py-2 text-sm max-w-[80%] ${
                      m.role === "user" ? "bg-primary text-primary-foreground" : "bg-card border"
                    }`}>
                      {m.content}
                    </div>
                  </div>
                ))}
                <div ref={chatEnd} />
              </div>

              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="Type a message..."
                  disabled={loading}
                />
                <Button onClick={sendMessage} disabled={loading || !input.trim()}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
