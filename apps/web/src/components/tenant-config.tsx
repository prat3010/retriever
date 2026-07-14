"use client";

import { useConfig, useUpdateConfig, type TenantConfig } from "@/hooks/use-config";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { useEffect, useState } from "react";

interface Props {
  tenantId: string;
}

export function ConfigTab({ tenantId }: Props) {
  const { data: config, isLoading } = useConfig(tenantId);
  const updateConfig = useUpdateConfig(tenantId);

  const [form, setForm] = useState<TenantConfig | null>(null);

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  function handleChange(path: string, value: string | number) {
    if (!form) return;
    const updated = structuredClone(form);

    if (path.startsWith("ai_provider.")) {
      const key = path.split(".")[1] as keyof typeof updated.ai_provider;
      (updated.ai_provider as Record<string, unknown>)[key] = value;
    } else if (path.startsWith("retrieval_settings.")) {
      const key = path.split(".")[1] as keyof typeof updated.retrieval_settings;
      (updated.retrieval_settings as Record<string, unknown>)[key] = Number(value);
    } else if (path.startsWith("security_settings.")) {
      const key = path.split(".")[1] as keyof typeof updated.security_settings;
      (updated.security_settings as Record<string, unknown>)[key] = Number(value);
    }

    setForm(updated);
  }

  function handleSave() {
    if (!form) return;
    updateConfig.mutate(form, {
      onSuccess: () => toast.success("Configuration updated"),
      onError: () => toast.error("Failed to update configuration"),
    });
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 w-full max-w-2xl" />
      </div>
    );
  }

  if (!form) {
    return (
      <p className="text-muted-foreground">
        No configuration found for this tenant.
      </p>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>AI Provider</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Default Model</Label>
            <Input
              id="model"
              value={form.ai_provider.default_model}
              onChange={(e) => handleChange("ai_provider.default_model", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="apiKey">API Key</Label>
            <Input
              id="apiKey"
              type="password"
              value={form.ai_provider.api_key ?? ""}
              onChange={(e) => handleChange("ai_provider.api_key", e.target.value)}
              placeholder="Leave blank to use platform default"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="baseUrl">Base URL</Label>
            <Input
              id="baseUrl"
              value={form.ai_provider.base_url ?? ""}
              onChange={(e) => handleChange("ai_provider.base_url", e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Retrieval Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="topK">Top K</Label>
            <Input
              id="topK"
              type="number"
              value={form.retrieval_settings.top_k}
              onChange={(e) => handleChange("retrieval_settings.top_k", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rrfK">RRF K</Label>
            <Input
              id="rrfK"
              type="number"
              value={form.retrieval_settings.rrf_k}
              onChange={(e) => handleChange("retrieval_settings.rrf_k", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="threshold">Reranking Threshold</Label>
            <Input
              id="threshold"
              type="number"
              step={0.05}
              value={form.retrieval_settings.reranking_threshold}
              onChange={(e) => handleChange("retrieval_settings.reranking_threshold", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="chunkSize">Chunk Size (tokens)</Label>
            <Input
              id="chunkSize"
              type="number"
              value={form.retrieval_settings.chunk_size ?? 500}
              onChange={(e) => handleChange("retrieval_settings.chunk_size", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="chunkOverlap">Chunk Overlap (tokens)</Label>
            <Input
              id="chunkOverlap"
              type="number"
              value={form.retrieval_settings.chunk_overlap ?? 100}
              onChange={(e) => handleChange("retrieval_settings.chunk_overlap", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="keyExpiration">API Key Expiration (days)</Label>
            <Input
              id="keyExpiration"
              type="number"
              value={form.security_settings.api_key_expiration_days}
              onChange={(e) => handleChange("security_settings.api_key_expiration_days", e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={updateConfig.isPending}>
        {updateConfig.isPending ? "Saving..." : "Save Configuration"}
      </Button>
    </div>
  );
}
