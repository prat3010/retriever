"use client";

import { useState, useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { Save, Loader2 } from "lucide-react";

interface GlobalConfig {
  ai_provider: { provider_name: string; api_key: string | null; base_url: string | null; default_model: string };
  embedding_provider: { provider_name: string; api_key: string | null; model_name: string; dimension: number };
  retrieval_settings: { top_k: number; rrf_k: number; reranking_threshold: number };
  security_settings: { enable_rls: boolean; api_key_expiration_days: number };
  rate_limits: { requests_per_minute: number; tokens_per_minute: number };
}

export default function SettingsPage() {
  const adminKey = useAuthStore((s) => s.adminKey);
  const router = useRouter();
  const [config, setConfig] = useState<GlobalConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (!adminKey) router.push("/login"); }, [adminKey, router]);

  useEffect(() => {
    if (!adminKey) return;
    api.get<GlobalConfig>("/v1/config/global")
      .then(setConfig)
      .catch(() => toast.error("Failed to load config"))
      .finally(() => setLoading(false));
  }, [adminKey]);

  if (!adminKey) return null;

  async function handleSave() {
    if (!config) return;
    setSaving(true);
    try {
      await api.put("/v1/config/global", config);
      toast.success("Global config updated");
    } catch {
      toast.error("Failed to save config");
    } finally {
      setSaving(false);
    }
  }

  function update<T>(path: string, value: T) {
    setConfig((prev) => {
      if (!prev) return prev;
      const keys = path.split(".");
      const copy = JSON.parse(JSON.stringify(prev));
      let obj = copy;
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]];
      obj[keys[keys.length - 1]] = value;
      return copy;
    });
  }

  if (loading) {
    return (
      <div>
        <Topbar title="Settings" description="Global platform configuration" />
        <div className="p-6 space-y-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Topbar title="Settings" description="Global platform configuration">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save Changes
        </Button>
      </Topbar>
      <div className="p-6 space-y-6 max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>AI Provider</CardTitle>
            <CardDescription>Default LLM provider and model for all tenants</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Provider</Label>
                <Input value={config?.ai_provider.provider_name ?? ""} onChange={(e) => update("ai_provider.provider_name", e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Default Model</Label>
                <Input value={config?.ai_provider.default_model ?? ""} onChange={(e) => update("ai_provider.default_model", e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>API Key</Label>
              <Input type="password" value={config?.ai_provider.api_key ?? ""} onChange={(e) => update("ai_provider.api_key", e.target.value)} placeholder="Leave blank to keep existing" />
            </div>
            <div className="space-y-2">
              <Label>Base URL</Label>
              <Input value={config?.ai_provider.base_url ?? ""} onChange={(e) => update("ai_provider.base_url", e.target.value)} placeholder="https://api.openai.com/v1" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Embedding Provider</CardTitle>
            <CardDescription>Vector embedding configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Provider</Label>
                <Input value={config?.embedding_provider.provider_name ?? ""} onChange={(e) => update("embedding_provider.provider_name", e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Model</Label>
                <Input value={config?.embedding_provider.model_name ?? ""} onChange={(e) => update("embedding_provider.model_name", e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Dimension</Label>
                <Input type="number" value={config?.embedding_provider.dimension ?? 768} onChange={(e) => update("embedding_provider.dimension", parseInt(e.target.value) || 768)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>API Key</Label>
              <Input type="password" value={config?.embedding_provider.api_key ?? ""} onChange={(e) => update("embedding_provider.api_key", e.target.value)} placeholder="Leave blank to keep existing" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retrieval Settings</CardTitle>
            <CardDescription>Search and reranking parameters</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Top K</Label>
              <Input type="number" value={config?.retrieval_settings.top_k ?? 10} onChange={(e) => update("retrieval_settings.top_k", parseInt(e.target.value) || 10)} />
            </div>
            <div className="space-y-2">
              <Label>RRF K</Label>
              <Input type="number" value={config?.retrieval_settings.rrf_k ?? 60} onChange={(e) => update("retrieval_settings.rrf_k", parseInt(e.target.value) || 60)} />
            </div>
            <div className="space-y-2">
              <Label>Rerank Threshold</Label>
              <Input type="number" step="0.1" value={config?.retrieval_settings.reranking_threshold ?? 0.7} onChange={(e) => update("retrieval_settings.reranking_threshold", parseFloat(e.target.value) || 0.7)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rate Limits</CardTitle>
            <CardDescription>Global API rate limiting</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Requests per minute</Label>
              <Input type="number" value={config?.rate_limits.requests_per_minute ?? 60} onChange={(e) => update("rate_limits.requests_per_minute", parseInt(e.target.value) || 60)} />
            </div>
            <div className="space-y-2">
              <Label>Tokens per minute</Label>
              <Input type="number" value={config?.rate_limits.tokens_per_minute ?? 100000} onChange={(e) => update("rate_limits.tokens_per_minute", parseInt(e.target.value) || 100000)} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
