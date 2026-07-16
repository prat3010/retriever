"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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

export default function SystemDataPage() {
  const adminKey = useAuthStore((s) => s.adminKey);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [resetConfirmText, setResetConfirmText] = useState("");
  const [showConfirmInput, setShowConfirmInput] = useState(false);

  useEffect(() => {
    if (!adminKey) router.push("/login");
  }, [adminKey, router]);

  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ["platform-stats"],
    queryFn: () => api.get<PlatformStats>("/v1/admin/platform/stats"),
    enabled: !!adminKey,
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

  if (!adminKey) return null;

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
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {statCards.map((card) => {
                const Icon = card.icon;
                return (
                  <Card key={card.title} className="hover:shadow-md transition-shadow duration-200">
                    <CardHeader className="flex flex-row items-start justify-between pb-2 space-y-0">
                      <div className="space-y-1">
                        <CardTitle className="text-base font-semibold">{card.title}</CardTitle>
                        <CardDescription className="text-xs">{card.description}</CardDescription>
                      </div>
                      <Icon className={`h-5 w-5 ${card.color}`} />
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

            {/* Danger Zone / Fresh Start Block */}
            <Card className="border-destructive/30 bg-destructive/5 overflow-hidden">
              <CardHeader className="border-b border-destructive/10 bg-destructive/10 pb-4">
                <div className="flex items-center gap-2 text-destructive">
                  <AlertTriangle className="h-5 w-5" />
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
                    <label className="text-xs font-semibold text-muted-foreground block">
                      Type <span className="font-bold text-destructive">RESET</span> below to confirm:
                    </label>
                    <input
                      type="text"
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
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
                  >
                    {resetMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Wiping Database...
                      </>
                    ) : (
                      <>
                        <RotateCcw className="mr-2 h-4 w-4" />
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
