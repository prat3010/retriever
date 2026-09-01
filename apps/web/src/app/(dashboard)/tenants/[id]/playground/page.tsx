"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth";
import { useTenant } from "@/hooks/use-tenants";
import { toast } from "sonner";
import { Send, Loader2, Terminal } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface EndpointDef {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  bodyPlaceholder: string;
}

const ENDPOINTS: Record<string, EndpointDef> = {
  search: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/search",
    bodyPlaceholder: JSON.stringify({ query: "architecture specification", limit: 5 }, null, 2),
  },
  chat: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/chat",
    bodyPlaceholder: JSON.stringify({ message: "What are the deliverables defined in the project scope?" }, null, 2),
  },
  rlm: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/rlm/analyze",
    bodyPlaceholder: JSON.stringify({ prompt: "Analyze and synthesize scope risks across all SOW documents", max_depth: 3 }, null, 2),
  },
  consensus: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/consensus/generate",
    bodyPlaceholder: JSON.stringify({ prompt: "Verify SLA data retention boundaries", generator_provider_name: "gemini", critic_provider_name: "openai" }, null, 2),
  },
  graphQuery: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/graph/query",
    bodyPlaceholder: JSON.stringify({ entity: "Retriever", max_hops: 2 }, null, 2),
  },
  projectEmbeddings: {
    method: "POST",
    path: "/v1/tenants/{tenantId}/embeddings/project",
    bodyPlaceholder: JSON.stringify({ method: "pca", dimensions: 2, normalize: true }, null, 2),
  },
  listDocuments: {
    method: "GET",
    path: "/v1/tenants/{tenantId}/documents",
    bodyPlaceholder: "",
  },
  getConfig: {
    method: "GET",
    path: "/v1/tenants/{tenantId}/config",
    bodyPlaceholder: "",
  },
  listApiKeys: {
    method: "GET",
    path: "/v1/admin/tenants/{tenantId}/api-keys",
    bodyPlaceholder: "",
  },
  listUsers: {
    method: "GET",
    path: "/v1/admin/tenants/{tenantId}/users",
    bodyPlaceholder: "",
  },
};

export default function PlaygroundPage() {
  const params = useParams();
  const tenantId = params.id as string;
  const { data: tenant } = useTenant(tenantId);
  const adminKey = useAuthStore((s) => s.adminKey);

  const [selected, setSelected] = useState("search");
  const [apiKey, setApiKey] = useState("");
  const [userId, setUserId] = useState("user_demo");
  const [body, setBody] = useState(ENDPOINTS["search"].bodyPlaceholder);
  const [response, setResponse] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const ep = ENDPOINTS[selected];

  async function handleSend() {
    setLoading(true);
    setResponse("");

    const path = ep.path.replace("{tenantId}", tenantId);
    const url = `${API_BASE}${path}`;

    const effectiveKey = apiKey.trim() || adminKey || "";

    try {
      const res = await fetch(url, {
        method: ep.method,
        headers: {
          "Content-Type": "application/json",
          ...(effectiveKey ? { Authorization: `Bearer ${effectiveKey}` } : {}),
          ...(apiKey.trim() ? { "X-API-Key": apiKey.trim() } : {}),
          "X-User-ID": userId.trim() || "admin_user",
          ...(adminKey ? { "X-Admin-Master-Key": adminKey } : {}),
        },
        ...(ep.method !== "GET" && ep.method !== "DELETE" && body.trim()
          ? { body }
          : {}),
      });
      const text = await res.text();
      setResponse(
        `${res.status} ${res.statusText}\n\n${text ? JSON.stringify(JSON.parse(text), null, 2) : "(empty)"}`
      );
    } catch (err) {
      setResponse(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  }


  return (
    <div>
      <Topbar
        title={`API Playground — ${tenant?.name ?? tenantId}`}
        description="Test endpoints with a tenant API key"
      />
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="h-4 w-4" /> Request
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Endpoint</Label>
                <Select value={selected} onValueChange={(v) => { setSelected(v); setBody(ENDPOINTS[v].bodyPlaceholder); setResponse(""); }}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="listDocuments">GET /documents</SelectItem>
                    <SelectItem value="search">POST /search</SelectItem>
                    <SelectItem value="getConfig">GET /config</SelectItem>
                    <SelectItem value="listApiKeys">GET /api-keys (admin)</SelectItem>
                    <SelectItem value="listUsers">GET /users (admin)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  placeholder="sk_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>User ID</Label>
                <Input
                  placeholder="user_123"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                />
              </div>
            </div>

            {ep.method !== "GET" && ep.method !== "DELETE" && (
              <div className="space-y-2">
                <Label>Request Body (JSON)</Label>
                <Textarea
                  className="font-mono text-xs h-32"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>
            )}

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <code className="rounded bg-muted px-2 py-1 text-xs">
                {ep.method} {ep.path.replace("{tenantId}", tenantId)}
              </code>
            </div>

            <Button onClick={handleSend} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              Send Request
            </Button>
          </CardContent>
        </Card>

        {response && (
          <Card>
            <CardHeader>
              <CardTitle>Response</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="rounded-lg bg-muted p-4 text-xs overflow-x-auto whitespace-pre-wrap font-mono">
                {response}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
