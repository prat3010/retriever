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
            <Label>n8n Target Webhook URL</Label>
            <Input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://n8n.your-domain.com/webhook/..."
            />
          </div>

          <Button onClick={handleSaveWebhook} disabled={configureMutation.isPending}>
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
    </div>
  );
}
