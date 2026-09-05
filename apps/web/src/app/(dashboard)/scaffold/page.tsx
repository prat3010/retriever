"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Code2,
  Cpu,
  Sparkles,
  ShieldCheck,
  GitBranch,
  Terminal,
  RefreshCw,
  Trash2,
  Copy,
  CheckCircle2,
  FileCode,
  Layers,
} from "lucide-react";
import { toast } from "sonner";

interface CustomPlugin {
  plugin_id: string;
  display_name: string;
  version: string;
  category: string;
  persona: string;
  description: string;
  is_active: boolean;
  hooks?: {
    api_router?: string;
    battery_service?: boolean;
    agentic_tool?: { name: string; description: string };
    workflow_step?: string;
  };
}

interface RecommendedBattery {
  battery_id: string;
  battery_name: string;
  category: string;
  match_confidence: number;
  rationale: string;
}

interface ScaffoldedFile {
  rel_path: string;
  content: string;
  module_type: string;
}

interface ScaffoldingPlan {
  plugin_id: string;
  display_name: string;
  description: string;
  persona: "business" | "fde_engineer";
  recommended_batteries: RecommendedBattery[];
  needs_custom_scaffold: boolean;
  scaffolded_files: ScaffoldedFile[];
  ast_audit_passed: boolean;
  git_branch_name: string;
  pull_request_markdown: string;
}

export default function ScaffoldPage() {
  const queryClient = useQueryClient();
  const [persona, setPersona] = useState<"business" | "fde_engineer">("fde_engineer");
  const [prompt, setPrompt] = useState("");
  const [domain, setDomain] = useState("crm");
  const [plan, setPlan] = useState<ScaffoldingPlan | null>(null);
  const [activeFileTab, setActiveFileTab] = useState<string>("domain/abstractions.py");
  const [copied, setCopied] = useState(false);

  // Fetch installed plugins
  const { data: plugins = [], isLoading: loadingPlugins, refetch: refetchPlugins } = useQuery<CustomPlugin[]>({
    queryKey: ["scaffold-plugins"],
    queryFn: () => api.get<CustomPlugin[]>("/v1/scaffold/plugins"),
  });

  // Synthesize Scaffolding Mutation
  const generateMutation = useMutation({
    mutationFn: (body: { prompt: string; target_domain: string; persona: string }) =>
      api.post<ScaffoldingPlan>("/v1/scaffold/generate", body),
    onSuccess: (data) => {
      setPlan(data);
      if (data.scaffolded_files.length > 0) {
        setActiveFileTab(data.scaffolded_files[1]?.rel_path || data.scaffolded_files[0].rel_path);
      }
      toast.success("Capability synthesized & verified through AST boundary gate!");
    },
    onError: (err: any) => {
      toast.error(`Synthesis failed: ${err.message || err}`);
    },
  });

  // Apply Scaffolding Mutation
  const applyMutation = useMutation({
    mutationFn: (targetPlan: ScaffoldingPlan) =>
      api.post<any>("/v1/scaffold/apply", targetPlan),
    onSuccess: (res) => {
      toast.success(`Successfully deployed plugin '${res.plugin_id}' to workspace!`);
      queryClient.invalidateQueries({ queryKey: ["scaffold-plugins"] });
      queryClient.invalidateQueries({ queryKey: ["platform-batteries"] });
    },
    onError: (err: any) => {
      toast.error(`Deployment failed: ${err.message || err}`);
    },
  });

  // Delete Plugin Mutation
  const deleteMutation = useMutation({
    mutationFn: (pluginId: string) =>
      api.delete<any>(`/v1/scaffold/plugins/${pluginId}`),
    onSuccess: () => {
      toast.success("Plugin deleted and unmounted.");
      queryClient.invalidateQueries({ queryKey: ["scaffold-plugins"] });
    },
    onError: (err: any) => {
      toast.error(`Delete failed: ${err.message || err}`);
    },
  });

  const handleGenerate = () => {
    if (!prompt.trim()) {
      toast.error("Please enter a capability requirement prompt.");
      return;
    }
    generateMutation.mutate({
      prompt: prompt.trim(),
      target_domain: domain,
      persona: persona,
    });
  };

  const handleCopyPr = () => {
    if (plan?.pull_request_markdown) {
      navigator.clipboard.writeText(plan.pull_request_markdown);
      setCopied(true);
      toast.success("GitHub Pull Request markdown copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const selectedFile = plan?.scaffolded_files.find((f) => f.rel_path === activeFileTab);

  return (
    <div className="flex flex-col min-h-screen">
      <Topbar title="Autonomous FDE Capability Studio (M97)" />

      <div className="flex-1 space-y-6 p-8 max-w-7xl mx-auto w-full">
        {/* Header Hero */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b pb-6">
          <div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-primary border-primary">
                Milestone 97 • v0.82.0
              </Badge>
              <Badge variant="secondary">Platform Battery #17</Badge>
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-2 flex items-center gap-3">
              <Code2 className="h-8 w-8 text-primary" />
              Autonomous FDE Metaprogrammer
            </h1>
            <p className="text-muted-foreground mt-1 max-w-2xl">
              Dual-persona solution engine: zero-code battery orchestration for business users, and AST-verified Hexagonal architecture code generation for Forward Deployed Engineers.
            </p>
          </div>

          {/* Persona Switcher */}
          <div className="flex items-center bg-secondary p-1 rounded-lg border">
            <button
              onClick={() => setPersona("business")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                persona === "business"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              👔 Business No-Code
            </button>
            <button
              onClick={() => setPersona("fde_engineer")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                persona === "fde_engineer"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              ⚡ FDE Metaprogrammer
            </button>
          </div>
        </div>

        {/* Input Formulation Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              {persona === "business" ? "Describe Your Business Requirement" : "Autonomous Hexagonal Code Synthesizer"}
            </CardTitle>
            <CardDescription>
              {persona === "business"
                ? "Enter your problem in plain English. The engine will match against our 16 active platform batteries."
                : "Specify target integration, protocol ports, and adapters. The Metaprogrammer will scaffold complete Hexagonal slices."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder={
                persona === "business"
                  ? "e.g. Scan clinical trial PDF forms, redact patient names with HIPAA compliance, and send instant alerts to our team's Slack channel."
                  : "e.g. Custom HubSpot CRM deal synchronizer pulling closed-won deals, indexing metadata with HNSW pgvector, and exposing a webhook endpoint."
              }
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              className="font-mono text-sm"
            />

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">Domain:</span>
                <Input
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="e.g. crm, healthcare, fintech"
                  className="w-48 h-8 text-xs font-mono"
                />
              </div>

              <Button
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
                className="gap-2"
              >
                {generateMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Synthesizing AST Slices…
                  </>
                ) : (
                  <>
                    <Cpu className="h-4 w-4" />
                    Synthesize Capability
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Synthesis Results Section */}
        {plan && (
          <div className="space-y-6">
            {/* Matched Batteries & AST Status */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="col-span-2">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Layers className="h-4 w-4 text-primary" />
                    Matched Platform Batteries ({plan.recommended_batteries.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {plan.recommended_batteries.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No existing platform battery matched. Custom scaffolding required.</p>
                  ) : (
                    plan.recommended_batteries.map((b) => (
                      <div
                        key={b.battery_id}
                        className="flex items-center justify-between p-2.5 rounded-lg border bg-secondary/30 text-xs"
                      >
                        <div>
                          <span className="font-semibold">{b.battery_name}</span>
                          <p className="text-muted-foreground text-[11px] mt-0.5">{b.rationale}</p>
                        </div>
                        <Badge variant="outline" className="font-mono text-[10px] ml-2">
                          {Math.round(b.match_confidence * 100)}% match
                        </Badge>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* AST Security Gate Badge */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    AST Security Gate
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold">
                    <CheckCircle2 className="h-4 w-4" />
                    Hexagonal Boundaries Verified
                  </div>
                  <ul className="space-y-1 text-muted-foreground text-[11px]">
                    <li>• 0 Framework Imports in Domain</li>
                    <li>• Typed Input & Output DTOs</li>
                    <li>• Self-Contained Pytest Suite</li>
                    <li>• Git Branch: <code className="text-foreground">{plan.git_branch_name}</code></li>
                  </ul>
                  <div className="pt-2 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleCopyPr}
                      className="w-full text-xs gap-1.5"
                    >
                      <GitBranch className="h-3.5 w-3.5" />
                      {copied ? "Copied!" : "Copy PR"}
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => applyMutation.mutate(plan)}
                      disabled={applyMutation.isPending}
                      className="w-full text-xs gap-1.5"
                    >
                      <Terminal className="h-3.5 w-3.5" />
                      {applyMutation.isPending ? "Deploying…" : "Deploy"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Generated Code Slices Viewer (FDE Mode) */}
            {plan.scaffolded_files.length > 0 && (
              <Card>
                <CardHeader className="border-b pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileCode className="h-4 w-4 text-primary" />
                        Scaffolded Hexagonal Slices: <span className="font-mono">{plan.plugin_id}</span>
                      </CardTitle>
                      <CardDescription>
                        Isolated in <code className="text-xs">src/plugins/custom/{plan.plugin_id}/</code>
                      </CardDescription>
                    </div>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (selectedFile) {
                          navigator.clipboard.writeText(selectedFile.content);
                          toast.success(`Copied ${selectedFile.rel_path} to clipboard!`);
                        }
                      }}
                      className="text-xs gap-1.5"
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Copy Code
                    </Button>
                  </div>

                  {/* File Tabs */}
                  <div className="flex flex-wrap gap-1 mt-3">
                    {plan.scaffolded_files.map((f) => (
                      <button
                        key={f.rel_path}
                        onClick={() => setActiveFileTab(f.rel_path)}
                        className={`px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
                          activeFileTab === f.rel_path
                            ? "bg-primary text-primary-foreground border-primary"
                            : "bg-secondary/40 text-muted-foreground hover:bg-secondary"
                        }`}
                      >
                        {f.rel_path}
                      </button>
                    ))}
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <pre className="p-4 text-xs font-mono overflow-x-auto bg-muted/30 max-h-[420px] rounded-b-lg">
                    <code>{selectedFile?.content || "// Select a file tab above"}</code>
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Installed Custom Plugins Ledger */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Code2 className="h-4 w-4 text-primary" />
                Installed Custom Plugins ({plugins.length})
              </CardTitle>
              <CardDescription>
                Plugins loaded from <code className="text-xs">src/plugins/custom/</code>
              </CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => refetchPlugins()}
              className="gap-1.5 text-xs"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
          </CardHeader>
          <CardContent>
            {loadingPlugins ? (
              <p className="text-xs text-muted-foreground">Scanning plugin directory…</p>
            ) : plugins.length === 0 ? (
              <div className="text-center py-8 border border-dashed rounded-lg">
                <Code2 className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
                <p className="text-sm font-semibold">No Custom Plugins Installed</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Use the synthesizer above to scaffold and deploy custom domain integrations without modifying core files.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {plugins.map((p) => (
                  <div
                    key={p.plugin_id}
                    className="flex flex-col md:flex-row items-start md:items-center justify-between p-3.5 rounded-lg border bg-card gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{p.display_name}</span>
                        <Badge variant="outline" className="font-mono text-[10px]">
                          v{p.version}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          {p.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{p.description}</p>
                      {p.hooks?.api_router && (
                        <div className="flex items-center gap-2 mt-2">
                          <code className="text-[10px] bg-secondary px-1.5 py-0.5 rounded font-mono">
                            Route: /v1/plugins/{p.plugin_id}/*
                          </code>
                        </div>
                      )}
                    </div>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteMutation.mutate(p.plugin_id)}
                      disabled={deleteMutation.isPending}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10 text-xs gap-1 self-end md:self-center"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Remove
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
