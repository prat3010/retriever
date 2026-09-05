"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, API_BASE } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  HardDrive,
  Cpu,
  Wifi,
  WifiOff,
  Download,
  RefreshCw,
  Search,
  Database,
  Layers,
  Sparkles,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

interface EdgeNode {
  node_id: string;
  tenant_id: string;
  device_name: string;
  platform: string;
  last_synced_seq: number;
  last_heartbeat_at: string;
  status: "online" | "offline";
  meta_data?: {
    tier?: string;
    client_version?: string;
    hardware_specs?: Record<string, any>;
  };
}

interface EdgeOverview {
  total_nodes: number;
  online_nodes: number;
  offline_nodes: number;
  total_checkpoints: number;
  platforms: Record<string, number>;
  tiers: Record<string, number>;
  nodes: EdgeNode[];
  battery?: {
    id: string;
    name: string;
    status: string;
    algorithm_foundation: string;
    latency_profile: string;
  };
}

interface EdgeSearchResult {
  results: Array<{
    chunk_id: string;
    document_id: string;
    content: string;
    score: number;
    vector_score: number;
    bm25_score: number;
    match_type: string;
  }>;
  total_hits: number;
  latency_ms: number;
  source: string;
  execution_tier: string;
  synthesized_answer: string;
}

export default function SovereignEdgePage() {
  const [selectedTenantId] = useState("00000000-0000-0000-0000-000000000001");
  const [simQuery, setSimQuery] = useState("Sovereign edge offline agent SQLite");
  const [isGeneratingBundle, setIsGeneratingBundle] = useState(false);

  // 1. Fetch Edge Overview
  const { data: overview, isLoading, refetch } = useQuery<EdgeOverview>({
    queryKey: ["admin", "edge", "overview"],
    queryFn: () => api.get<EdgeOverview>("/v1/admin/edge/overview"),
    refetchInterval: 15000,
  });

  // 2. Simulated Edge Search Mutation
  const searchMutation = useMutation<EdgeSearchResult, Error, string>({
    mutationFn: (queryText) =>
      api.post<EdgeSearchResult>(`/v1/tenants/${selectedTenantId}/edge/search`, {
        query: queryText,
        top_k: 4,
        use_hybrid: true,
        alpha: 0.5,
      }),
    onSuccess: () => {
      toast.success("Edge simulation query executed offline!");
    },
    onError: (err) => {
      toast.error(`Search simulation failed: ${err.message}`);
    },
  });

  // 3. 1-Click Standalone SQLite Bundle Exporter
  const handleDownloadBundle = async () => {
    try {
      setIsGeneratingBundle(true);
      toast.info("Compiling standalone SQLite bundle (FTS5 + binary vector blobs)...");
      const key = useAuthStore.getState().adminKey || "";
      const res = await fetch(`${API_BASE}/v1/tenants/${selectedTenantId}/edge/bundle?download=true`, {
        method: "POST",
        headers: {
          "X-Admin-Master-Key": key,
        },
      });
      if (!res.ok) {
        throw new Error(`Failed to download bundle: HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `retriever-edge-${selectedTenantId.slice(0, 8)}.sqlite`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success("Standalone sovereign .sqlite database bundle downloaded!");
    } catch (err: any) {
      toast.error(`Bundle export failed: ${err.message}`);
    } finally {
      setIsGeneratingBundle(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Topbar title="Sovereign Edge SQLite & Vector Sync" />

      <main className="flex-1 space-y-6 p-6">
        {/* Header */}
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold flex items-center gap-2">
              <HardDrive className="h-7 w-7 text-primary" />
              Sovereign Edge SQLite & Offline-First Node Sync
            </h1>
            <p className="text-sm text-muted-foreground">
              Milestone 98 (Platform Battery #18): Distributed embedded SQLite databases with FTS5, binary float32 vector storage, and differential sequence synchronization.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={handleDownloadBundle}
              disabled={isGeneratingBundle}
              className="gap-2 bg-primary font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Download className="h-4 w-4" />
              {isGeneratingBundle ? "Compiling Bundle..." : "Export .sqlite Bundle"}
            </Button>
          </div>
        </div>

        {/* Top Metrics Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Edge Nodes</CardTitle>
              <Cpu className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview?.total_nodes ?? 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {overview?.online_nodes ?? 0} active | {overview?.offline_nodes ?? 0} offline
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Sync Checkpoints</CardTitle>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{overview?.total_checkpoints ?? 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                SHA-256 cryptographically verified deltas
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Platform Battery #18</CardTitle>
              <Zap className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold">ACTIVE</span>
                <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">
                  {overview?.battery?.latency_profile ?? "~2ms"}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1 truncate">
                {overview?.battery?.algorithm_foundation ?? "Embedded SQLite FTS5 + Vector Cosine"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Offline Resilience</CardTitle>
              <WifiOff className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">100% Sovereign</div>
              <p className="text-xs text-muted-foreground mt-1">
                Zero cloud dependency during network partition
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Two Columns: Node Registry & Edge Simulator */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Edge Node Registry */}
          <Card className="flex flex-col">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                Registered Sovereign Edge Nodes
              </CardTitle>
              <CardDescription>
                Edge client runtimes syncing local SQLite vector indexes with central cloud pgvector.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1">
              {overview?.nodes && overview.nodes.length > 0 ? (
                <div className="divide-y rounded-md border text-sm">
                  {overview.nodes.map((node) => (
                    <div key={node.node_id} className="flex items-center justify-between p-3.5">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 font-medium">
                          <span>{node.device_name}</span>
                          <Badge variant="secondary" className="text-xs">
                            {node.platform}
                          </Badge>
                          <Badge variant="outline" className="text-[10px] uppercase font-mono">
                            {node.meta_data?.tier || "hybrid_cache"}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                          ID: {node.node_id.slice(0, 16)}... | Watermark Seq: {node.last_synced_seq}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {node.status === "online" ? (
                          <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 gap-1">
                            <Wifi className="h-3 w-3" /> Online
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-muted-foreground gap-1">
                            <WifiOff className="h-3 w-3" /> Offline
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-center border rounded-lg border-dashed">
                  <Cpu className="h-10 w-10 text-muted-foreground/40 mb-2" />
                  <p className="text-sm font-medium text-foreground">No Edge Nodes Registered Yet</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Edge runtimes auto-register on first heartbeat pull (`/v1/tenants/{"{id}"}/edge/nodes/register`).
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sovereign Edge Search Simulator */}
          <Card className="flex flex-col">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Offline Hybrid Search Simulation
              </CardTitle>
              <CardDescription>
                Simulate local embedded SQLite hybrid search combining FTS5 BM25 with binary vector cosine dot product.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 flex-1">
              <div className="flex gap-2">
                <Input
                  value={simQuery}
                  onChange={(e) => setSimQuery(e.target.value)}
                  placeholder="Enter edge test query..."
                  className="flex-1"
                />
                <Button
                  onClick={() => searchMutation.mutate(simQuery)}
                  disabled={searchMutation.isPending}
                  className="gap-2"
                >
                  <Search className="h-4 w-4" />
                  {searchMutation.isPending ? "Searching..." : "Simulate"}
                </Button>
              </div>

              {searchMutation.data && (
                <div className="space-y-3 rounded-lg border p-4 bg-muted/30">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-foreground">Offline Search Results</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono text-[10px]">
                        Latency: {searchMutation.data.latency_ms}ms
                      </Badge>
                      <Badge variant="secondary" className="font-mono text-[10px]">
                        {searchMutation.data.source}
                      </Badge>
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground italic">
                    {searchMutation.data.synthesized_answer}
                  </p>

                  <div className="space-y-2">
                    {searchMutation.data.results.map((item) => (
                      <div key={item.chunk_id} className="rounded border bg-card p-2.5 text-xs space-y-1">
                        <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                          <span>Chunk: {item.chunk_id.slice(0, 12)}...</span>
                          <span className="text-primary font-semibold">
                            Score: {item.score.toFixed(4)} ({item.match_type})
                          </span>
                        </div>
                        <p className="text-foreground line-clamp-2">{item.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
