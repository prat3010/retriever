"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Send, Loader2, Terminal } from "lucide-react";
import { useUsers } from "@/hooks/use-users";

export function TenantSandboxTab({ tenantId }: { tenantId: string }) {
  const { data: users, isLoading: loadingUsers } = useUsers(tenantId);
  const [apiKey, setApiKey] = useState("");
  const [userId, setUserId] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Derive effective user ID from state or auto-select first active user
  const effectiveUserId = userId || (users && users.length > 0 ? users[0].userId : "");

  useEffect(() => { chatEnd.current?.scrollIntoView(); }, [messages]);

  async function startSession() {
    if (!apiKey.trim()) { toast.error("Enter a tenant API key first"); return; }
    if (!effectiveUserId.trim()) { toast.error("Enter or select a user ID"); return; }
    setCreatingSession(true);
    try {
      const res = await fetch(`${API_BASE}/v1/tenants/${tenantId}/chat/sessions`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${apiKey.trim()}`, "X-User-ID": effectiveUserId.trim(), "Content-Type": "application/json" },
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
          "X-User-ID": effectiveUserId.trim(),
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
            <Terminal className="h-4 w-4" aria-hidden="true" /> RAG Sandbox
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!sessionId && (
            <div className="space-y-3">
              <div>
                <Label htmlFor="sandbox-api-key">Tenant API Key</Label>
                <Input
                  id="sandbox-api-key"
                  placeholder="sk_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="sandbox-user-select">User Context (Select or Enter User ID)</Label>
                {users && users.length > 0 ? (
                  <Select value={effectiveUserId} onValueChange={(val) => setUserId(val)}>
                    <SelectTrigger id="sandbox-user-select" className="mt-1">
                      <SelectValue placeholder="Select a tenant user..." />
                    </SelectTrigger>
                    <SelectContent>
                      {users.map((u) => (
                        <SelectItem key={u.userId} value={u.userId}>
                          {u.displayName || u.externalId} ({u.userId.slice(0, 8)}...)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id="sandbox-user-select"
                    className="mt-1"
                    placeholder="User UUID (e.g., 00000000-0000-0000-0000-000000000001)"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                  />
                )}
                {loadingUsers && (
                  <p className="text-xs text-muted-foreground mt-1">Loading registered tenant users...</p>
                )}
              </div>

              <Button onClick={startSession} disabled={creatingSession}>
                {creatingSession ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                {creatingSession ? "Starting..." : "Start Session"}
              </Button>
            </div>
          )}

          {sessionId && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Session: {sessionId.slice(0, 8)}...</span>
                <Button variant="outline" size="sm" onClick={() => { setSessionId(null); setMessages([]); }} aria-label="Start new chat session">
                  New Session
                </Button>
              </div>

              <div
                role="log"
                aria-live="polite"
                aria-label="Conversation messages"
                className="rounded-lg border bg-muted/30 p-4 max-h-64 overflow-y-auto space-y-2"
              >
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
                  id="sandbox-chat-input"
                  aria-label="Type a message"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="Type a message..."
                  disabled={loading}
                />
                <Button onClick={sendMessage} disabled={loading || !input.trim()} aria-label="Send message">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
