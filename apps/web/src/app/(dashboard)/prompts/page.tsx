"use client";

import { useState } from "react";
import {
  Sparkles,
  Zap,
  Play,
  RotateCcw,
  Trash2,
  ChevronDown,
  ChevronUp,
  Cpu,
  TrendingUp,
  Clock,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { useTenants } from "@/hooks/use-tenants";
import {
  useCompiledPrompts,
  useActiveCompiledPrompt,
  useCompilePrompt,
  useActivateCompiledPrompt,
  useDeactivateCompiledPrompt,
  useDeleteCompiledPrompt,
} from "@/hooks/use-prompts";

export default function PromptsOptimizationPage() {
  const { data: tenantsData } = useTenants("", 100, 0);
  const tenants = tenantsData?.items || [];
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");

  // Default to first tenant once loaded
  const tenantId = selectedTenantId || tenants[0]?.tenantId || "tn_demo_enterprise";

  // Form State
  const [programName, setProgramName] = useState<string>("rag_cot_optimized");
  const [optimizer, setOptimizer] = useState<"BootstrapFewShot" | "MIPROv2" | "RandomSearch">("BootstrapFewShot");
  const [metricTarget, setMetricTarget] = useState<"composite" | "faithfulness" | "context_relevance">("composite");
  const [maxDemos, setMaxDemos] = useState<number>(3);
  const [expandedProgramId, setExpandedProgramId] = useState<string | null>(null);

  // Queries
  const { data: programs = [], isLoading: loadingPrograms } = useCompiledPrompts(tenantId);
  const { data: activeProgram } = useActiveCompiledPrompt(tenantId);

  // Mutations
  const compileMutation = useCompilePrompt(tenantId);
  const activateMutation = useActivateCompiledPrompt(tenantId);
  const deactivateMutation = useDeactivateCompiledPrompt(tenantId);
  const deleteMutation = useDeleteCompiledPrompt(tenantId);

  const handleCompile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await compileMutation.mutateAsync({
        name: programName.trim() || "rag_cot_optimized",
        optimizer,
        metric_target: metricTarget,
        max_demos: maxDemos,
      });
      toast.success(
        `Optimization Complete! Accuracy improved from ${(res.baseline_score * 100).toFixed(1)}% to ${(res.compiled_score * 100).toFixed(1)}% (+${res.improvement_pct.toFixed(1)}%)`
      );
      setExpandedProgramId(res.program_id);
    } catch (err: any) {
      toast.error(err.message || "Prompt compilation failed.");
    }
  };

  const handleActivate = async (programId: string) => {
    try {
      await activateMutation.mutateAsync(programId);
      toast.success("Program hot-activated in live production!");
    } catch (err: any) {
      toast.error(err.message || "Failed to activate program.");
    }
  };

  const handleDeactivate = async (programId: string) => {
    try {
      await deactivateMutation.mutateAsync(programId);
      toast.info("Program deactivated. Reverted to standard handcrafted template.");
    } catch (err: any) {
      toast.error(err.message || "Failed to deactivate program.");
    }
  };

  const handleDelete = async (programId: string) => {
    if (!confirm("Are you sure you want to delete this compiled prompt program?")) return;
    try {
      await deleteMutation.mutateAsync(programId);
      toast.success("Compiled prompt program deleted.");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete program.");
    }
  };

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold font-heading tracking-tight">
                DSPy Declarative Prompt Compilation
              </h1>
              <p className="text-sm text-muted-foreground">
                Algorithmic prompt self-optimization using metric-driven teleprompters (BootstrapFewShot & MIPROv2).
              </p>
            </div>
          </div>
        </div>

        {/* Tenant Selector */}
        <div className="flex items-center gap-3">
          <Label className="text-xs uppercase text-muted-foreground font-semibold">Tenant:</Label>
          <Select
            value={tenantId}
            onValueChange={(val) => {
              setSelectedTenantId(val);
              setExpandedProgramId(null);
            }}
          >
            <SelectTrigger className="w-[220px]">
              <SelectValue placeholder="Select Tenant" />
            </SelectTrigger>
            <SelectContent>
              {tenants.map((t) => (
                <SelectItem key={t.tenantId} value={t.tenantId}>
                  {t.name || t.tenantId}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Production Status Banner */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start sm:items-center gap-3">
              <div
                className={`p-2.5 rounded-full ${
                  activeProgram
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                }`}
              >
                {activeProgram ? <Zap className="h-5 w-5" /> : <RotateCcw className="h-5 w-5" />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-foreground">Active Production State</h3>
                  <Badge variant={activeProgram ? "default" : "secondary"}>
                    {activeProgram ? "DSPy Program Active" : "Default Handcrafted Fallback"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {activeProgram ? (
                    <>
                      Live chat inference is grounded with{" "}
                      <span className="font-medium text-foreground">{activeProgram.name}</span> (
                      {activeProgram.optimizer}, {activeProgram.few_shot_demos.length} few-shot demonstrations,{" "}
                      {(activeProgram.compiled_score * 100).toFixed(1)}% {activeProgram.metric_name} score).
                    </>
                  ) : (
                    "Inference is using standard handcrafted PromptTemplate string templates. Activate a compiled program below to enforce metric-verified grounding."
                  )}
                </p>
              </div>
            </div>

            {activeProgram && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDeactivate(activeProgram.program_id)}
                disabled={deactivateMutation.isPending}
              >
                Deactivate & Revert
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Compiler Control Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Cpu className="h-5 w-5 text-primary" />
            Teleprompter Optimization Cockpit
          </CardTitle>
          <CardDescription>
            Bootstrap high-leverage system prompt instructions and discover faithful few-shot exemplars.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCompile} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="program-name" className="text-xs font-semibold">
                  Program Name
                </Label>
                <Input
                  id="program-name"
                  value={programName}
                  onChange={(e) => setProgramName(e.target.value)}
                  placeholder="support_cot_v1"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-semibold">Optimization Strategy</Label>
                <Select
                  value={optimizer}
                  onValueChange={(val: "BootstrapFewShot" | "MIPROv2" | "RandomSearch") => setOptimizer(val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="BootstrapFewShot">BootstrapFewShot (Exemplar Curation)</SelectItem>
                    <SelectItem value="MIPROv2">MIPROv2 (Joint Prompt & Demo Search)</SelectItem>
                    <SelectItem value="RandomSearch">RandomSearch (Fast Demonstration Shuffle)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-semibold">Target Metric</Label>
                <Select
                  value={metricTarget}
                  onValueChange={(val: "composite" | "faithfulness" | "context_relevance") => setMetricTarget(val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="composite">Composite (Faithfulness + Token Recall)</SelectItem>
                    <SelectItem value="faithfulness">Faithfulness (Strict Grounding)</SelectItem>
                    <SelectItem value="context_relevance">Context Relevance (Anti-Hallucination)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="max-demos" className="text-xs font-semibold">
                  Max Demonstrations
                </Label>
                <Input
                  id="max-demos"
                  type="number"
                  min={1}
                  max={8}
                  value={maxDemos}
                  onChange={(e) => setMaxDemos(Number(e.target.value))}
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t">
              <div className="text-xs text-muted-foreground">
                Teleprompter runs dual-stage evaluation on tenant dataset to prevent overfitting.
              </div>
              <Button type="submit" disabled={compileMutation.isPending} className="gap-2">
                {compileMutation.isPending ? (
                  <>
                    <Cpu className="h-4 w-4 animate-spin" /> Compiling Prompt Program...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" /> Compile & Optimize
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Versioned Programs Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold font-heading flex items-center gap-2">
            <Layers className="h-5 w-5 text-muted-foreground" />
            Compiled Prompt Programs ({programs.length})
          </h2>
          <Badge variant="outline" className="text-xs font-mono">
            Tenant: {tenantId}
          </Badge>
        </div>

        {loadingPrograms ? (
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              Loading compiled prompt programs...
            </CardContent>
          </Card>
        ) : programs.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center space-y-3">
              <div className="mx-auto w-10 h-10 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
                <Sparkles className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-foreground">No Compiled Programs Yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Trigger prompt compilation above to discover optimized instructions and few-shot exemplars for this tenant.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {programs.map((prog) => {
              const isExpanded = expandedProgramId === prog.program_id;
              return (
                <Card
                  key={prog.program_id}
                  className={`transition-all ${
                    prog.is_active
                      ? "border-emerald-500/40 bg-emerald-500/[0.02]"
                      : "hover:border-border/80"
                  }`}
                >
                  <CardHeader className="p-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-base text-foreground">{prog.name}</h3>
                          <Badge variant={prog.is_active ? "default" : "secondary"} className="text-xs">
                            {prog.is_active ? "Active in Production" : "Inactive"}
                          </Badge>
                          <Badge variant="outline" className="text-xs font-mono">
                            {prog.optimizer}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-3">
                          <span className="flex items-center gap-1 font-mono">
                            <Clock className="h-3 w-3" /> {new Date(prog.created_at).toLocaleString()}
                          </span>
                          <span>•</span>
                          <span className="font-mono">{prog.program_id}</span>
                        </div>
                      </div>

                      {/* Score Metrics */}
                      <div className="flex items-center gap-6">
                        <div className="flex items-center gap-4 px-4 py-2 rounded-lg bg-secondary/50 border">
                          <div className="text-center">
                            <div className="text-[10px] uppercase text-muted-foreground font-semibold">Baseline</div>
                            <div className="text-sm font-mono font-medium text-muted-foreground">
                              {(prog.baseline_score * 100).toFixed(1)}%
                            </div>
                          </div>
                          <div className="text-muted-foreground font-mono">→</div>
                          <div className="text-center">
                            <div className="text-[10px] uppercase text-emerald-600 dark:text-emerald-400 font-semibold">
                              Compiled
                            </div>
                            <div className="text-base font-mono font-bold text-emerald-600 dark:text-emerald-400">
                              {(prog.compiled_score * 100).toFixed(1)}%
                            </div>
                          </div>
                          <div className="flex items-center gap-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                            <TrendingUp className="h-3 w-3" />
                            +{prog.improvement_pct.toFixed(1)}%
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2">
                          {prog.is_active ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeactivate(prog.program_id)}
                              disabled={deactivateMutation.isPending}
                            >
                              Deactivate
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handleActivate(prog.program_id)}
                              disabled={activateMutation.isPending}
                              className="gap-1.5"
                            >
                              <Zap className="h-3.5 w-3.5" /> Activate
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setExpandedProgramId(isExpanded ? null : prog.program_id)}
                          >
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </Button>

                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(prog.program_id)}
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  {/* Expanded Demonstration & Instruction Drawer */}
                  {isExpanded && (
                    <CardContent className="px-6 pb-6 pt-0 border-t space-y-4">
                      <div className="mt-4 space-y-2">
                        <Label className="text-xs font-semibold text-muted-foreground uppercase">
                          Compiled System Instruction
                        </Label>
                        <div className="p-3 rounded bg-secondary/70 font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed border">
                          {prog.compiled_instruction}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-xs font-semibold text-muted-foreground uppercase flex items-center gap-1.5">
                          Curated Few-Shot Demonstrations ({prog.few_shot_demos.length})
                        </Label>

                        {prog.few_shot_demos.length === 0 ? (
                          <p className="text-xs text-muted-foreground italic">No few-shot demonstrations saved.</p>
                        ) : (
                          <div className="grid grid-cols-1 gap-3">
                            {prog.few_shot_demos.map((demo, idx) => (
                              <div
                                key={idx}
                                className="p-3.5 rounded-lg border bg-card/60 text-xs space-y-2"
                              >
                                <div className="flex items-center justify-between text-muted-foreground">
                                  <span className="font-semibold text-foreground">Exemplar #{idx + 1}</span>
                                  {demo.score !== undefined && (
                                    <Badge variant="outline" className="font-mono text-[10px]">
                                      Score: {(demo.score * 100).toFixed(0)}%
                                    </Badge>
                                  )}
                                </div>

                                <div className="space-y-1">
                                  <span className="font-semibold text-foreground/80">Question:</span>
                                  <p className="text-muted-foreground">{demo.question}</p>
                                </div>

                                <div className="space-y-1">
                                  <span className="font-semibold text-foreground/80">Context:</span>
                                  <p className="text-muted-foreground/80 line-clamp-2">{demo.context}</p>
                                </div>

                                {demo.thought && (
                                  <div className="space-y-1">
                                    <span className="font-semibold text-foreground/80">Reasoning (CoT):</span>
                                    <p className="text-muted-foreground italic">{demo.thought}</p>
                                  </div>
                                )}

                                <div className="space-y-1">
                                  <span className="font-semibold text-foreground/80">Answer:</span>
                                  <p className="text-foreground font-medium">{demo.answer}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
