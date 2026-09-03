"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useState } from "react";
import {
  useClusterRegions,
  useProbeRegions,
  usePreviewRouting,
} from "@/hooks/use-regions";
import {
  Database,
  Building2,
  FileText,
  Key,
  Users,
  MessageSquare,
  ClipboardList,
  Binary,
  AlertTriangle,
  RotateCcw,
  Loader2,
  Cloud,
  ShieldCheck,
  FileArchive,
  CheckCircle2,
  Play,
  Globe,
  Compass,
  Zap,
  Network,
} from "lucide-react";

interface PlatformStats {
  tenants: { total: number; active: number; suspended: number };
  documents: { total: number };
  chunks: { total: number };
  vectors: { total: number };
  apiKeys: { total: number };
  users: { total: number };
  chat: { sessions: number; messages: number };
  auditLogs: { total: number };
  evaluations: { runs: number };
}

interface BackupSnapshot {
  snapshot_id: string;
  timestamp: string;
  tables: string[];
  row_counts: Record<string, number>;
  uncompressed_bytes: number;
  compressed_bytes: number;
  sha256_checksum: string;
  encryption_algorithm: string;
  storage_uri: string;
  status: string;
  duration_seconds: number;
}

export default function SystemDataPage() {
  const queryClient = useQueryClient();
  const [resetConfirmText, setResetConfirmText] = useState("");
  const [showConfirmInput, setShowConfirmInput] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState("US");

  const { data: clusterRegions, isLoading: regionsLoading } = useClusterRegions();
  const probeRegionsMutation = useProbeRegions();
  const previewRoutingMutation = usePreviewRouting();

  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: () => api.get<PlatformStats>("/v1/admin/platform/stats"),
  });

  const { data: backups, isLoading: backupsLoading, refetch: refetchBackups } = useQuery({
    queryKey: ["platform-backups"],
    queryFn: () => api.get<BackupSnapshot[]>("/v1/admin/platform/backups"),
  });

  const backupMutation = useMutation({
    mutationFn: () => api.post<{ snapshot_id: string; status: string; message: string }>("/v1/admin/platform/backups/trigger", {}),
    onSuccess: (res) => {
      toast.success(res.message || "Encrypted snapshot generated successfully!");
      refetchBackups();
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to create database snapshot.");
    },
  });

  const dryRunMutation = useMutation({
    mutationFn: (snapshotId: string) =>
      api.post<{ status: string; message: string }>("/v1/admin/platform/backups/restore", {
        snapshot_id: snapshotId,
        dry_run: true,
      }),
    onSuccess: (res) => {
      toast.success(res.message || "Dry-run restore verification passed!");
    },
    onError: (err: any) => {
      toast.error(err.message || "Dry-run restore failed.");
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => api.post<{ status: string; message: string }>("/v1/admin/platform/reset"),
    onSuccess: (res) => {
      toast.success(res.message || "Platform reset successfully completed!");
      refetch();
      queryClient.invalidateQueries();
      setShowConfirmInput(false);
      setResetConfirmText("");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to reset platform data.");
    },
  });

  const handleResetClick = () => {
    if (!showConfirmInput) {
      setShowConfirmInput(true);
      return;
    }

    if (resetConfirmText.trim().toLowerCase() !== "reset") {
      toast.error('Please type "RESET" to confirm this action.');
      return;
    }

    if (window.confirm("CRITICAL WARNING: This will permanently delete all customer workspaces, documents, API keys, and chunk indexes. Only the system meta-tenant will be preserved. Are you absolutely sure?")) {
      resetMutation.mutate();
    }
  };

  const statCards = stats
    ? [
        {
          title: "Tenant Spaces",
          description: "Active customer workspaces",
          icon: Building2,
          color: "text-blue-500",
          stats: [
            { label: "Total", value: stats.tenants.total },
            { label: "Active", value: stats.tenants.active },
            { label: "Suspended", value: stats.tenants.suspended },
          ],
        },
        {
          title: "Ingested Content",
          description: "Tenant files and documents",
          icon: FileText,
          color: "text-indigo-500",
          stats: [
            { label: "Documents", value: stats.documents.total },
          ],
        },
        {
          title: "Index Slices",
          description: "Token slices and embeddings",
          icon: Binary,
          color: "text-violet-500",
          stats: [
            { label: "Text Chunks", value: stats.chunks.total },
            { label: "Vector Records", value: stats.vectors.total },
          ],
        },
        {
          title: "Identity & Credentials",
          description: "Access keys and user accounts",
          icon: Key,
          color: "text-emerald-500",
          stats: [
            { label: "API Keys", value: stats.apiKeys.total },
            { label: "Platform Users", value: stats.users.total },
          ],
        },
        {
          title: "Inference Conversations",
          description: "LLM sessions and messages",
          icon: MessageSquare,
          color: "text-amber-500",
          stats: [
            { label: "Chat Sessions", value: stats.chat.sessions },
            { label: "Messages", value: stats.chat.messages },
          ],
        },
        {
          title: "Platform Logs",
          description: "Audit ledger records",
          icon: ClipboardList,
          color: "text-rose-500",
          stats: [
            { label: "Audit Logs", value: stats.auditLogs.total },
            { label: "Evaluation Runs", value: stats.evaluations.runs },
          ],
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <Topbar title="System Data Explorer" description="Explore database statistics and platform status in one place">
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          Refresh Stats
        </Button>
      </Topbar>

      <div className="p-6 space-y-8">
        {isLoading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44 w-full" />
            ))}
          </div>
        ) : (
          <>
            {/* Stats Dashboard Grid */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3" aria-busy={isLoading}>
              {statCards.map((card) => {
                const Icon = card.icon;
                return (
                  <Card key={card.title} className="hover:shadow-md transition-shadow duration-200">
                    <CardHeader className="flex flex-row items-start justify-between pb-2 space-y-0">
                      <div className="space-y-1">
                        <CardTitle className="text-base font-semibold">{card.title}</CardTitle>
                        <CardDescription className="text-xs">{card.description}</CardDescription>
                      </div>
                      <Icon className={`h-5 w-5 ${card.color}`} aria-hidden="true" />
                    </CardHeader>
                    <CardContent className="pt-4 border-t mt-2">
                      <div className="grid grid-cols-2 gap-4">
                        {card.stats.map((item) => (
                          <div key={item.label} className="space-y-1">
                            <span className="text-xs text-muted-foreground font-medium">{item.label}</span>
                            <div className="text-xl font-bold tracking-tight">{item.value}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Disaster Recovery & Cloud Database Snapshots Block (M87) */}
            <Card className="border-border/60 bg-card overflow-hidden">
              <CardHeader className="border-b border-border/40 pb-4 flex flex-row items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Cloud className="h-5 w-5 text-emerald-500" aria-hidden="true" />
                    <CardTitle className="text-base font-semibold">Disaster Recovery & Encrypted Cloud Snapshots (M87)</CardTitle>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 font-mono border border-emerald-500/20">
                      AES-256 GCM
                    </span>
                  </div>
                  <CardDescription className="text-xs">
                    Automated pooler-safe database dumps with cryptographic SHA-256 verification and Cloudflare R2 / AWS S3 archival.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => backupMutation.mutate()}
                  disabled={backupMutation.isPending}
                  className="gap-2"
                >
                  {backupMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                      Dumping & Encrypting...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-4 w-4 text-emerald-500" />
                      Trigger On-Demand Backup
                    </>
                  )}
                </Button>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="flex items-center justify-between text-xs text-muted-foreground border-b border-border/40 pb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span>Storage Engine: <strong className="text-foreground">AES-256 GCM Encrypted Vault (Local & S3/R2 Ready)</strong></span>
                  </div>
                  <span>Continuous WAL Archival & PITR Recovery Engine</span>
                </div>

                <div className="bg-muted/40 border border-border/40 rounded-lg p-3 text-xs space-y-1 text-muted-foreground">
                  <div className="font-semibold text-foreground flex items-center gap-1.5">
                    <span>💡 Cloud Replication Setup (Cloudflare R2 / AWS S3 / MinIO)</span>
                  </div>
                  <p className="leading-relaxed">
                    By default, snapshots are encrypted with AES-256 and saved locally to <code className="bg-background px-1 py-0.5 rounded font-mono text-foreground">/tmp/retriever/backups</code>.
                    To enable automatic off-site cloud sync, configure <code className="bg-background px-1 py-0.5 rounded font-mono text-foreground">STORAGE_PROVIDER=&quot;s3&quot;</code> and S3/R2 credentials in your server <code className="bg-background px-1 py-0.5 rounded font-mono text-foreground">.env</code>.
                    Full instructions in <code className="text-foreground font-medium">docs/runbooks/DISASTER_RECOVERY_AND_BACKUPS.md</code>.
                  </p>
                </div>

                {backupsLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : !backups || backups.length === 0 ? (
                  <div className="text-center py-6 text-sm text-muted-foreground border border-dashed rounded-lg">
                    No snapshot archives registered yet. Click &quot;Trigger On-Demand Backup&quot; to create your first encrypted snapshot.
                  </div>
                ) : (
                  <div className="rounded-md border border-border/40 overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-muted/50 text-muted-foreground font-medium border-b border-border/40">
                        <tr>
                          <th className="p-3">Snapshot ID</th>
                          <th className="p-3">Timestamp (UTC)</th>
                          <th className="p-3">Tables</th>
                          <th className="p-3">Encrypted Size</th>
                          <th className="p-3">SHA-256 Digest</th>
                          <th className="p-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/30 font-mono">
                        {backups.map((snap) => (
                          <tr key={snap.snapshot_id} className="hover:bg-muted/30 transition-colors">
                            <td className="p-3 font-semibold text-foreground flex items-center gap-2">
                              <FileArchive className="h-4 w-4 text-muted-foreground" />
                              {snap.snapshot_id}
                            </td>
                            <td className="p-3 text-muted-foreground">
                              {new Date(snap.timestamp).toLocaleString()}
                            </td>
                            <td className="p-3">
                              <span className="text-foreground font-sans bg-muted px-1.5 py-0.5 rounded">
                                {snap.tables.length} tables
                              </span>
                            </td>
                            <td className="p-3 text-muted-foreground">
                              {(snap.compressed_bytes / 1024).toFixed(1)} KB
                            </td>
                            <td className="p-3 text-muted-foreground truncate max-w-[120px]" title={snap.sha256_checksum}>
                              {snap.sha256_checksum.slice(0, 12)}...
                            </td>
                            <td className="p-3 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => dryRunMutation.mutate(snap.snapshot_id)}
                                disabled={dryRunMutation.isPending}
                                className="h-7 px-2 text-xs font-sans gap-1 text-emerald-600 hover:text-emerald-500 hover:bg-emerald-500/10"
                                title="Run dry-run cryptographic integrity and schema audit"
                              >
                                <Play className="h-3 w-3" />
                                Audit Restore
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Geo-Distributed Edge Routing & Multi-Region Read-Replicas (M89) */}
            <Card className="border-border/60 bg-card overflow-hidden">
              <CardHeader className="border-b border-border/40 pb-4 flex flex-row items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Globe className="h-5 w-5 text-primary" aria-hidden="true" />
                    <CardTitle className="text-base font-semibold">
                      Geo-Distributed Edge Routing & Read-Replica Topology (M89)
                    </CardTitle>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono border border-primary/20">
                      Sub-30ms Global Latency
                    </span>
                  </div>
                  <CardDescription className="text-xs">
                    Multi-region edge network routing read queries and vector lookups to localized replicas based on Geo-IP country headers.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => probeRegionsMutation.mutate()}
                  disabled={probeRegionsMutation.isPending}
                  className="gap-2"
                >
                  {probeRegionsMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      Probing Latency...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 text-primary" />
                      Probe Regional Latency
                    </>
                  )}
                </Button>
              </CardHeader>
              <CardContent className="p-6 space-y-6">
                {/* 3-Region Status Cards Grid */}
                <div className="grid gap-4 sm:grid-cols-3">
                  {clusterRegions?.regions ? (
                    clusterRegions.regions.map((reg) => (
                      <div
                        key={reg.region_code}
                        className={`p-4 rounded-lg border text-xs space-y-2.5 ${
                          reg.is_primary
                            ? "bg-primary/5 border-primary/40"
                            : reg.is_configured
                            ? "bg-muted/40 border-border/60"
                            : "bg-muted/20 border-border/30 opacity-80"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5 font-bold text-foreground">
                            <Compass className="h-4 w-4 text-primary" />
                            <span>{reg.region_name}</span>
                          </div>
                          {reg.is_primary ? (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-primary text-primary-foreground font-semibold">
                              PRIMARY MASTER
                            </span>
                          ) : (
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                                reg.status === "healthy"
                                  ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                                  : "bg-muted text-muted-foreground"
                              }`}
                            >
                              {reg.is_configured ? "EDGE REPLICA" : "FALLBACK MASTER"}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1 text-muted-foreground">
                          <div className="flex justify-between">
                            <span>Hub:</span>
                            <strong className="text-foreground font-medium">{reg.city}</strong>
                          </div>
                          <div className="flex justify-between font-mono text-[11px]">
                            <span>Endpoint:</span>
                            <span className="text-foreground truncate max-w-[140px]">{reg.endpoint_display}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>RTT Latency:</span>
                            <strong className="text-emerald-500 font-mono">
                              {reg.latency_ms ? `${reg.latency_ms} ms` : "15 ms (Local)"}
                            </strong>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} className="h-28 w-full" />
                    ))
                  )}
                </div>

                {/* Interactive Geo-IP Simulation Console */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Network className="h-4 w-4 text-primary" />
                      <span className="font-semibold text-xs text-foreground uppercase tracking-wider">
                        Geo-IP Routing & Latency Reduction Simulator
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      Header: x-vercel-ip-country / cf-ipcountry
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {[
                      { code: "US", label: "United States (US)" },
                      { code: "GB", label: "United Kingdom (GB)" },
                      { code: "DE", label: "Germany (DE)" },
                      { code: "IN", label: "India (IN)" },
                      { code: "JP", label: "Japan (JP)" },
                      { code: "AU", label: "Australia (AU)" },
                      { code: "BR", label: "Brazil (BR)" },
                    ].map((item) => (
                      <Button
                        key={item.code}
                        size="sm"
                        variant={selectedCountry === item.code ? "default" : "outline"}
                        onClick={() => {
                          setSelectedCountry(item.code);
                          previewRoutingMutation.mutate(item.code);
                        }}
                        className="text-xs h-7"
                      >
                        {item.label}
                      </Button>
                    ))}
                  </div>

                  {previewRoutingMutation.data && (
                    <div className="p-3 bg-background rounded border border-border/60 text-xs font-mono space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span>
                          Origin: <strong>{previewRoutingMutation.data.client_country}</strong> ({previewRoutingMutation.data.detected_continent})
                        </span>
                        <span>
                          Target: <strong className="text-primary">{previewRoutingMutation.data.selected_region}</strong>
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground line-through">
                            {previewRoutingMutation.data.estimated_primary_latency_ms} ms
                          </span>
                          <span className="text-emerald-500 font-bold">
                            &rarr; {previewRoutingMutation.data.estimated_replica_latency_ms} ms
                          </span>
                          {previewRoutingMutation.data.estimated_reduction_pct > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-500 font-bold border border-emerald-500/30">
                              -{previewRoutingMutation.data.estimated_reduction_pct}% Faster
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {previewRoutingMutation.data.routing_reason}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Danger Zone / Fresh Start Block */}
            <Card className="border-destructive/30 bg-destructive/5 overflow-hidden">
              <CardHeader className="border-b border-destructive/10 bg-destructive/10 pb-4">
                <div className="flex items-center gap-2 text-destructive">
                  <AlertTriangle className="h-5 w-5" aria-hidden="true" />
                  <CardTitle className="text-base font-semibold">Danger Zone: Platform Fresh Start</CardTitle>
                </div>
                <CardDescription className="text-destructive/80 text-xs">
                  This action permanently resets the database and filesystem storage to factory defaults.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
                  Resetting the platform will **permanently delete** all standard tenant workspaces, their uploaded documents, vector slice indexes, generated API keys, registered users, and conversation history. 
                  Only the default **System Tenant** (<code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono select-all">00000000-0000-0000-0000-000000000000</code>) is preserved.
                </p>

                {showConfirmInput && (
                  <div className="space-y-2 max-w-sm">
                    <Label htmlFor="reset-confirm-input" className="text-xs font-semibold text-muted-foreground block">
                      Type <span className="font-bold text-destructive">RESET</span> below to confirm:
                    </Label>
                    <Input
                      id="reset-confirm-input"
                      type="text"
                      className="h-9"
                      placeholder="RESET"
                      value={resetConfirmText}
                      onChange={(e) => setResetConfirmText(e.target.value)}
                    />
                  </div>
                )}

                <div className="flex gap-3">
                  <Button
                    variant="destructive"
                    onClick={handleResetClick}
                    disabled={resetMutation.isPending}
                    aria-label={showConfirmInput ? "Confirm database wipe and reset" : "Initiate platform reset"}
                  >
                    {resetMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        Wiping Database...
                      </>
                    ) : (
                      <>
                        <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                        {showConfirmInput ? "Confirm Wipe & Reset" : "Reset Platform Data"}
                      </>
                    )}
                  </Button>
                  {showConfirmInput && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowConfirmInput(false);
                        setResetConfirmText("");
                      }}
                      disabled={resetMutation.isPending}
                    >
                      Cancel
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
