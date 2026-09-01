"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLiveTelemetry } from "@/hooks/use-telemetry";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Trash2, Loader2, Zap } from "lucide-react";


interface TenantTelemetryTabProps {
  tenantId: string;
}

export function TenantTelemetryTab({ tenantId }: TenantTelemetryTabProps) {
  const queryClient = useQueryClient();
  const { data: telemetry, isLoading } = useLiveTelemetry(tenantId);

  const { data: cacheStats, refetch: refetchCacheStats } = useQuery({
    queryKey: ["tenant-cache-stats", tenantId],
    queryFn: () => api.get<{ status: string; total_vectors: number }>(`/v1/tenants/${tenantId}/cache/stats`),
    enabled: !!tenantId,
  });

  const purgeCacheMutation = useMutation({
    mutationFn: () => api.post<{ status: string; purged: boolean; deleted_count?: number }>(`/v1/tenants/${tenantId}/cache/purge`),
    onSuccess: (res) => {
      toast.success(res.deleted_count ? `Purged ${res.deleted_count} semantic cache vectors.` : "Semantic cache successfully purged.");
      refetchCacheStats();
      queryClient.invalidateQueries({ queryKey: ["live-telemetry", tenantId] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to purge semantic cache.");
    },
  });


  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-36 w-full" />
        </div>
      </div>
    );
  }

  const p99 = telemetry?.p99_latency_ms ?? 0;
  const hallucinationIndex = (telemetry?.hallucination_index ?? 0) * 100;
  const faithfulness = (telemetry?.avg_faithfulness ?? 1.0) * 100;
  const precision = (telemetry?.avg_precision ?? 1.0) * 100;
  const satisfaction = telemetry?.satisfaction_rate ?? 100;
  const tokensUsed = telemetry?.monthly_tokens_used ?? 0;
  const cacheHits = telemetry?.cache_hits ?? 0;
  const latencySaved = telemetry?.latency_saved_ms ?? 0;
  const costSaved = telemetry?.cost_saved_usd ?? 0.0;
  const storageMb = ((telemetry?.storage_bytes_used ?? 0) / (1024 * 1024)).toFixed(2);
  const docCount = telemetry?.documents_count ?? 0;

  // Compute overall SLA Status
  let slaStatus: "compliant" | "warning" | "breach" = "compliant";
  if (p99 > 5000 || hallucinationIndex > 30) {
    slaStatus = "breach";
  } else if (p99 > 2500 || hallucinationIndex > 15) {
    slaStatus = "warning";
  }

  return (
    <div className="space-y-6">
      {/* 1. Header SLA Operational Banner */}
      <Card className="border-l-4 border-l-primary shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <span>🛰️ Retriever Deep Observability Cockpit</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono font-normal">
                  Live Stream (15s polling)
                </span>
              </CardTitle>
              <CardDescription className="text-xs">
                Real-time OpenTelemetry aggregations, latency SLAs, semantic cache savings, and cognitive quality metrics.
              </CardDescription>
            </div>
            <div>
              {slaStatus === "compliant" && (
                <Badge variant="outline" className="text-emerald-600 border-emerald-500 bg-emerald-500/10 text-xs px-3 py-1">
                  🟢 SLA Fully Compliant
                </Badge>
              )}
              {slaStatus === "warning" && (
                <Badge variant="outline" className="text-amber-600 border-amber-500 bg-amber-500/10 text-xs px-3 py-1">
                  🟡 SLA Warning (P99 / Hallucination Spike)
                </Badge>
              )}
              {slaStatus === "breach" && (
                <Badge variant="destructive" className="text-xs px-3 py-1">
                  🔴 SLA Incident Breach
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* 2. Top-Level Core SLA Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">P99 Inference Latency</CardDescription>
            <CardTitle className="text-2xl font-mono">
              {p99 > 0 ? `${p99.toFixed(0)} ms` : "< 120 ms"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-[11px] text-muted-foreground">
            Target SLA: &lt; 2,500 ms &bull; Real-time OTel
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Hallucination Index</CardDescription>
            <CardTitle className={`text-2xl font-mono ${hallucinationIndex > 20 ? "text-rose-500" : "text-emerald-500"}`}>
              {hallucinationIndex.toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-[11px] text-muted-foreground">
            Target: &lt; 15% &bull; Calibrated Semantic NLI
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Avg Faithfulness Score</CardDescription>
            <CardTitle className="text-2xl font-mono text-emerald-500">
              {faithfulness.toFixed(1)}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-[11px] text-muted-foreground">
            Verified claim entailment ratio
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">User Satisfaction (CSAT)</CardDescription>
            <CardTitle className="text-2xl font-mono text-blue-500">
              {satisfaction.toFixed(0)}%
            </CardTitle>
          </CardHeader>
          <CardContent className="text-[11px] text-muted-foreground">
            👍 {telemetry?.thumbs_up ?? 0} &nbsp;|&nbsp; 👎 {telemetry?.thumbs_down ?? 0} rated
          </CardContent>
        </Card>
      </div>

      {/* 3. Detailed Sections: Semantic Cache & Ingestion Health */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Semantic Cache Performance */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span>⚡ Semantic Cache & Cost Optimization</span>
              <Badge variant="outline" className="text-xs font-mono">
                {cacheHits} Cache Hits
              </Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Sub-millisecond cosine vector lookup deduplication saving LLM compute.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="rounded-lg bg-muted/40 p-3 border">
                <span className="text-xs text-muted-foreground block">Latency Saved</span>
                <span className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  {(latencySaved / 1000).toFixed(1)} s
                </span>
              </div>
              <div className="rounded-lg bg-muted/40 p-3 border">
                <span className="text-xs text-muted-foreground block">Cost Saved (USD)</span>
                <span className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  ${costSaved.toFixed(3)}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-2 border-t text-xs">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Cached Vector Entities:</span>
                <Badge variant="secondary" className="font-mono text-xs">
                  {cacheStats?.total_vectors ?? 0} vectors
                </Badge>
              </div>
              <Button
                variant="destructive"
                size="sm"
                className="text-xs h-7 px-2.5"
                disabled={purgeCacheMutation.isPending}
                onClick={() => purgeCacheMutation.mutate()}
              >
                {purgeCacheMutation.isPending ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Purging...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-3 w-3 mr-1" />
                    Purge Cache
                  </>
                )}
              </Button>
            </div>
            <div className="text-[11px] text-muted-foreground">
              Semantic Cache intercepts vector similarities ($&ge; \tau$) to serve responses under 5ms without token expense.
            </div>
          </CardContent>
        </Card>


        {/* Token Quotas & Knowledge Index */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span>📦 Vector Storage & Token Consumption</span>
              <Badge variant="outline" className="text-xs font-mono">
                {docCount} Documents
              </Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Multi-tenant pgvector indexing storage and monthly token burn volume.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="rounded-lg bg-muted/40 p-3 border">
                <span className="text-xs text-muted-foreground block">Tokens Consumed</span>
                <span className="text-lg font-bold font-mono">
                  {tokensUsed.toLocaleString()}
                </span>
              </div>
              <div className="rounded-lg bg-muted/40 p-3 border">
                <span className="text-xs text-muted-foreground block">Vector Storage</span>
                <span className="text-lg font-bold font-mono">
                  {storageMb} MB
                </span>
              </div>
            </div>
            <div className="text-xs text-muted-foreground pt-1">
              Context Precision across retrieved chunks: <span className="font-semibold text-foreground">{precision.toFixed(1)}%</span>.
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 4. SLA Alert Incident Feed & Webhook Dispatch Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">🚨 SLA Alert Incident Trigger Rules</CardTitle>
          <CardDescription className="text-xs">
            Automated multi-channel webhook dispatch triggers monitoring cognitive fidelity and quota abuse.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded border bg-card">
              <div className="space-y-0.5">
                <div className="font-semibold">Rolling Hallucination Breach Alert</div>
                <div className="text-muted-foreground">Triggers webhook when 1-hour rolling hallucination index exceeds 30%</div>
              </div>
              <Badge variant="outline" className="border-emerald-500 text-emerald-600 font-mono">Active Sentinel</Badge>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded border bg-card">
              <div className="space-y-0.5">
                <div className="font-semibold">P99 Latency SLA Degradation</div>
                <div className="text-muted-foreground">Triggers webhook when stage-2 reranking or inference P99 latency exceeds 5,000ms</div>
              </div>
              <Badge variant="outline" className="border-emerald-500 text-emerald-600 font-mono">Active Sentinel</Badge>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded border bg-card">
              <div className="space-y-0.5">
                <div className="font-semibold">Token Quota Exhaustion Guard (90% / 100%)</div>
                <div className="text-muted-foreground">Warns client administrator at 90% quota and soft-throttles at 100% capacity</div>
              </div>
              <Badge variant="outline" className="border-emerald-500 text-emerald-600 font-mono">Active Sentinel</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
