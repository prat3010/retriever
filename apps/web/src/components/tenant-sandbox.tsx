"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Send, Loader2, Terminal } from "lucide-react";
import { api } from "@/lib/api";

export function TenantSandboxTab({ tenantId }: { tenantId: string }) {
  const [apiKey, setApiKey] = useState("");
  const [userId, setUserId] = useState("admin_demo");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => { chatEnd.current?.scrollIntoView(); }, [messages]);

  async function startSession() {
    if (!apiKey.trim()) { toast.error("Enter a tenant API key first"); return; }
    if (!userId.trim()) { toast.error("Enter a user ID"); return; }
    setCreatingSession(true);
    try {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/chat/sessions`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${apiKey.trim()}`, "X-User-ID": userId.trim(), "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSessionId(data.sessionId);
      setMessages([{ role: "assistant", content: `Session started: ${data.sessionId}` }]);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setCreatingSession(false);
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
          "Authorization": `Bearer ${apiKey.trim()}`,
          "X-User-ID": userId.trim(),
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ query: msg }),
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
              try {
                const parsed = JSON.parse(data);
                if (parsed.event === "done") break;
                full += parsed.delta ?? parsed.content ?? "";
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
              <Input
                placeholder="sk_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <Label>User ID</Label>
              <Input
                placeholder="user_123"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
              />
              <Button onClick={startSession} disabled={creatingSession}>
                {creatingSession ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {creatingSession ? "Starting..." : "Start Session"}
              </Button>
            </div>
          )}

          {sessionId && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Session: {sessionId.slice(0, 8)}...</span>
                <Button variant="outline" size="sm" onClick={() => { setSessionId(null); setMessages([]); }}>New Session</Button>
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
