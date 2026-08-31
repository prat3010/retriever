"use client";

import { useConfig, useUpdateConfig, type TenantConfig } from "@/hooks/use-config";
import { useLoraAdapters, useTrainLoraAdapter, useActivateLoraAdapter } from "@/hooks/use-lora";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useEffect, useState, useMemo } from "react";
import { PROVIDERS, providerByBaseUrl } from "@/lib/providers";

interface Props {
  tenantId: string;
}

export function ConfigTab({ tenantId }: Props) {
  const { data: config, isLoading } = useConfig(tenantId);
  const updateConfig = useUpdateConfig(tenantId);
  const { data: loraAdapters } = useLoraAdapters(tenantId);
  const trainLora = useTrainLoraAdapter(tenantId);
  const activateLora = useActivateLoraAdapter(tenantId);

  const [form, setForm] = useState<TenantConfig | null>(null);
  const [customBaseUrl, setCustomBaseUrl] = useState(false);
  const [isTrainOpen, setIsTrainOpen] = useState(false);
  const [adapterName, setAdapterName] = useState("SOW & Software Architecture Adapter");
  const [domainTag, setDomainTag] = useState("software_architecture");
  const [loraRank, setLoraRank] = useState(8);

  const detectedProvider = useMemo(() => {
    if (!form) return undefined;
    return providerByBaseUrl(form.ai_provider.base_url ?? "");
  }, [form]);

  const showCustomUrl = useMemo(() => {
    if (!form) return false;
    return customBaseUrl || !detectedProvider;
  }, [customBaseUrl, detectedProvider, form]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync server data to local form state
    if (config) setForm(config);
  }, [config]);

  function setProvider(value: string) {
    if (!form) return;
    if (value === "__custom__") {
      setCustomBaseUrl(true);
      return;
    }
    setCustomBaseUrl(false);
    const provider = PROVIDERS.find((p) => p.value === value);
    if (!provider) return;
    const updated = structuredClone(form);
    updated.ai_provider.base_url = provider.baseUrl;
    updated.ai_provider.default_model = provider.defaultModel;
    setForm(updated);
  }

  function handleChange(path: string, value: string | number | boolean) {
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
      (updated.security_settings as Record<string, unknown>)[key] = typeof value === "boolean" ? value : Number(value);
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
            <Label htmlFor="provider">Provider</Label>
            <Select value={detectedProvider?.value ?? "__custom__"} onValueChange={setProvider}>
              <SelectTrigger id="provider">
                <SelectValue placeholder="Select a provider..." />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
          {showCustomUrl && (
            <div className="space-y-2">
              <Label htmlFor="baseUrl">Base URL</Label>
              <Input
                id="baseUrl"
                value={form.ai_provider.base_url ?? ""}
                onChange={(e) => handleChange("ai_provider.base_url", e.target.value)}
                placeholder="https://api.openai.com/v1"
              />
            </div>
          )}
          {!showCustomUrl && form.ai_provider.base_url && (
            <p className="text-xs text-muted-foreground">
              Base URL: {form.ai_provider.base_url}
              <Button variant="link" size="sm" className="h-auto p-0 ml-2 text-xs" onClick={() => setCustomBaseUrl(true)}>Edit</Button>
            </p>
          )}
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

      {/* M79: Hybrid Search & LoRA Domain Embedding Calibration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Sparse-Dense Hybrid & LoRA Calibration</CardTitle>
              <CardDescription className="text-xs">
                Tune the convex linear ratio (α) between dense semantic vectors and sublinear BM25 keyword tokens, and calibrate domain LoRA residual adapters.
              </CardDescription>
            </div>
            <Badge variant="outline" className="font-mono text-xs">
              α = {(form.retrieval_settings.hybrid_alpha ?? 0.7).toFixed(2)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <Label htmlFor="hybridAlpha">Hybrid Search Balance Ratio (α)</Label>
              <span className="text-muted-foreground font-mono text-[11px]">
                {((form.retrieval_settings.hybrid_alpha ?? 0.7) * 100).toFixed(0)}% Dense (Semantic) / {((1 - (form.retrieval_settings.hybrid_alpha ?? 0.7)) * 100).toFixed(0)}% Sparse (BM25)
              </span>
            </div>
            <input
              id="hybridAlpha"
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              className="w-full accent-primary cursor-pointer"
              value={form.retrieval_settings.hybrid_alpha ?? 0.7}
              onChange={(e) => handleChange("retrieval_settings.hybrid_alpha", parseFloat(e.target.value))}
            />
            <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
              <span>0.0 (Pure Keyword/Code)</span>
              <span>0.5 (Balanced)</span>
              <span>1.0 (Pure Dense Vector)</span>
            </div>
          </div>

          <div className="space-y-2 pt-2 border-t">
            <div className="flex justify-between items-center">
              <div>
                <Label>Active LoRA Domain Adapter</Label>
                <p className="text-[11px] text-muted-foreground">
                  Residual projection layer calibrating local embeddings to technical SOW and architecture terms.
                </p>
              </div>
              <Dialog open={isTrainOpen} onOpenChange={setIsTrainOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-xs">
                    ⚡ Train New Adapter
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="text-base">Train Contrastive LoRA Domain Adapter</DialogTitle>
                    <DialogDescription className="text-xs">
                      Runs MultipleNegativesRankingLoss on domain contrastive pairs to calibrate local vector representations.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-3 pt-2">
                    <div className="space-y-1">
                      <Label htmlFor="adName" className="text-xs">Adapter Name</Label>
                      <Input
                        id="adName"
                        value={adapterName}
                        onChange={(e) => setAdapterName(e.target.value)}
                        placeholder="e.g. SOW Architecture Adapter"
                        className="text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="adDomain" className="text-xs">Domain Tag</Label>
                      <Input
                        id="adDomain"
                        value={domainTag}
                        onChange={(e) => setDomainTag(e.target.value)}
                        placeholder="e.g. software_architecture"
                        className="text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="adRank" className="text-xs">LoRA Rank (r)</Label>
                      <Select value={String(loraRank)} onValueChange={(v) => setLoraRank(Number(v))}>
                        <SelectTrigger id="adRank" className="text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="4">r = 4 (Ultra Lightweight)</SelectItem>
                          <SelectItem value="8">r = 8 (Recommended)</SelectItem>
                          <SelectItem value="16">r = 16 (High Capacity)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button
                      className="w-full text-xs mt-2"
                      disabled={trainLora.isPending}
                      onClick={() => {
                        trainLora.mutate(
                          { name: adapterName, domain_tag: domainTag, rank: loraRank, epochs: 15, learning_rate: 0.001 },
                          {
                            onSuccess: (res) => {
                              toast.success(`Adapter '${res.name}' trained with loss ${res.loss_score}`);
                              setIsTrainOpen(false);
                            },
                            onError: (err) => toast.error(`Training failed: ${err.message}`),
                          }
                        );
                      }}
                    >
                      {trainLora.isPending ? "Training LoRA Layer..." : "Start Calibration Run"}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <Select
              value={form.retrieval_settings.active_lora_adapter || "none"}
              onValueChange={(val) => {
                const updated = val === "none" ? null : val;
                handleChange("retrieval_settings.active_lora_adapter", updated ?? "");
                if (updated) {
                  activateLora.mutate(updated, {
                    onSuccess: () => toast.success("Active LoRA adapter set"),
                  });
                }
              }}
            >
              <SelectTrigger className="text-xs">
                <SelectValue placeholder="Select active adapter (or Base nomic-embed-text)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Base Local Model (Zero-Residual Identity)</SelectItem>
                {(loraAdapters || []).map((ad) => (
                  <SelectItem key={ad.adapter_id} value={ad.adapter_id}>
                    {ad.name} (r={ad.rank}, {ad.domain_tag})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <input
              id="enableRls"
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={form.security_settings.enable_rls}
              onChange={(e) => handleChange("security_settings.enable_rls", e.target.checked)}
            />
            <Label htmlFor="enableRls">Enable Row-Level Security</Label>
          </div>
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
