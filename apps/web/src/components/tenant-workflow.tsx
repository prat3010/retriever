"use client";

import { useState } from "react";
import { useConfigureN8nWebhook, useN8nSpec } from "@/hooks/use-workflow";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface TenantWorkflowTabProps {
  tenantId: string;
}

export function TenantWorkflowTab({ tenantId }: TenantWorkflowTabProps) {
  const [webhookUrl, setWebhookUrl] = useState("https://n8n.example.com/webhook/retriever-events");
  const configureMutation = useConfigureN8nWebhook(tenantId);
  const { data: n8nSpec } = useN8nSpec();

  const handleSaveWebhook = () => {
    if (!webhookUrl.trim()) return;
    configureMutation.mutate(webhookUrl);
  };

  return (
    <div className="space-y-6">
      {/* Outbound n8n Webhook Configuration Card */}
      <Card>
        <CardHeader>
          <CardTitle>Outbound n8n Webhook Configuration</CardTitle>
          <CardDescription>Configure external n8n HTTP webhook endpoint for negative feedback and escalation event triggers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="n8n-webhook-url">n8n Target Webhook URL</Label>
            <Input
              id="n8n-webhook-url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://n8n.your-domain.com/webhook/..."
            />
          </div>

          <Button onClick={handleSaveWebhook} disabled={configureMutation.isPending} aria-label="Save and ping n8n webhook">
            {configureMutation.isPending ? "Testing & Saving..." : "Save & Ping n8n Webhook"}
          </Button>

          {configureMutation.data && (
            <div className="p-4 bg-muted rounded-lg space-y-2 text-sm font-mono">
              <div className="flex items-center gap-2">
                <Badge variant={configureMutation.data.ping_result.success ? "outline" : "destructive"}>
                  {configureMutation.data.ping_result.success ? "✅ Ping Success" : "❌ Ping Failed"}
                </Badge>
                <span className="text-xs text-muted-foreground">Status: {configureMutation.data.status}</span>
              </div>
              <p className="text-xs text-muted-foreground">Linked URL: {configureMutation.data.n8n_webhook_url}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 1-Click n8n OpenAPI Spec Viewer Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>n8n HTTP Node OpenAPI 3.0 Specification</CardTitle>
            <CardDescription>Copyable OpenAPI schema for 1-click import into n8n workflow HTTP nodes.</CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigator.clipboard.writeText(JSON.stringify(n8nSpec, null, 2))}
            aria-label="Copy n8n OpenAPI 3.0 Specification JSON"
          >
            Copy Spec JSON
          </Button>
        </CardHeader>
        <CardContent>
          <pre className="p-4 bg-muted rounded-lg font-mono text-xs max-h-96 overflow-auto">
            {n8nSpec ? JSON.stringify(n8nSpec, null, 2) : "Loading n8n OpenAPI Specification..."}
          </pre>
        </CardContent>
      </Card>

      {/* Durable Background AI Workflows & Checkpoint Engine (Milestone 95) */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <span>⚡</span> Durable Background AI Workflows & Checkpoint Engine
              </CardTitle>
              <CardDescription>
                Step-level memoization, resilient automatic retry backoff, and idempotent checkpoint state machines (Platform Battery #15).
              </CardDescription>
            </div>
            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-300">
              Battery #15 Active
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 border rounded-lg bg-card">
              <div className="text-xs text-muted-foreground uppercase font-semibold">Engine Status</div>
              <div className="text-lg font-bold font-mono text-emerald-600">Active & Serving</div>
              <div className="text-xs text-muted-foreground mt-1">Tenant-isolated via Postgres RLS</div>
            </div>
            <div className="p-3 border rounded-lg bg-card">
              <div className="text-xs text-muted-foreground uppercase font-semibold">Checkpoint Backend</div>
              <div className="text-lg font-bold font-mono">PostgreSQL 16</div>
              <div className="text-xs text-muted-foreground mt-1">Step memoization enabled</div>
            </div>
            <div className="p-3 border rounded-lg bg-card">
              <div className="text-xs text-muted-foreground uppercase font-semibold">Blueprints In Stock</div>
              <div className="text-lg font-bold font-mono">4 Blueprints</div>
              <div className="text-xs text-muted-foreground mt-1">Ingest, Graph, Eval, Re-embed</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground uppercase">Tenant REST API Endpoints</div>
            <div className="bg-muted p-3 rounded-lg font-mono text-xs space-y-1 overflow-x-auto">
              <div><span className="text-blue-500 font-bold">GET</span>  /v1/tenants/{tenantId}/workflows/blueprints</div>
              <div><span className="text-emerald-600 font-bold">POST</span> /v1/tenants/{tenantId}/workflows/:workflow_name/run</div>
              <div><span className="text-blue-500 font-bold">GET</span>  /v1/tenants/{tenantId}/workflows/executions</div>
              <div><span className="text-blue-500 font-bold">GET</span>  /v1/tenants/{tenantId}/workflows/executions/:id</div>
              <div><span className="text-amber-500 font-bold">POST</span> /v1/tenants/{tenantId}/workflows/executions/:id/retry</div>
              <div><span className="text-red-500 font-bold">POST</span> /v1/tenants/{tenantId}/workflows/executions/:id/cancel</div>
              <div><span className="text-purple-500 font-bold">POST</span> /v1/tenants/{tenantId}/workflows/events</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
