"use client";

import { useState } from "react";
import {
  Bot,
  Play,
  CheckCircle2,
  AlertTriangle,
  History,
  RotateCcw,
  Check,
  X,
  RefreshCw,
  Cpu,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  useAgentTools,
  useExecuteWorkflow,
  useResumeWorkflow,
  useThreadHistory,
  useRollbackThread,
  AgentExecutionResult,
} from "@/hooks/use-agentic";

export default function OrchestrationPage() {
  const [tenantId, setTenantId] = useState("tn_demo_enterprise");
  const [prompt, setPrompt] = useState("");
  const [threadId, setThreadId] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);

  // Execution state
  const [executionResult, setExecutionResult] = useState<AgentExecutionResult | null>(null);
  const [approvalComment, setApprovalComment] = useState("");
  const [editedArgsJson, setEditedArgsJson] = useState("");

  // Queries & Mutations
  const { data: tools = [], isLoading: loadingTools } = useAgentTools(tenantId);
  const { data: history, refetch: refetchHistory } = useThreadHistory(tenantId, threadId || executionResult?.thread_id || "");
  const executeMutation = useExecuteWorkflow();
  const resumeMutation = useResumeWorkflow();
  const rollbackMutation = useRollbackThread();

  const handleRun = async (overridePrompt?: string) => {
    const target = overridePrompt || prompt;
    if (!target.trim() || !tenantId) return;

    try {
      const res = await executeMutation.mutateAsync({
        tenantId,
        prompt: target,
        threadId: threadId || undefined,
        allowedTools: selectedTools.length > 0 ? selectedTools : undefined,
      });
      setExecutionResult(res);
      setThreadId(res.thread_id);

      if (res.pending_approval) {
        setEditedArgsJson(JSON.stringify(res.pending_approval.arguments, null, 2));
        setApprovalComment("");
      }
      refetchHistory();
    } catch {
      // Handled by react-query error state
    }
  };

  const handleResume = async (decision: "approve" | "reject") => {
    if (!executionResult?.pending_approval) return;
    const pending = executionResult.pending_approval;

    let modifiedArgs = undefined;
    if (decision === "approve" && editedArgsJson.trim()) {
      try {
        modifiedArgs = JSON.parse(editedArgsJson);
      } catch {
        alert("Invalid JSON in edited arguments.");
        return;
      }
    }

    try {
      const res = await resumeMutation.mutateAsync({
        tenantId,
        threadId: executionResult.thread_id,
        actionId: pending.action_id,
        decision,
        modifiedArguments: modifiedArgs,
        comment: approvalComment.trim() || undefined,
      });
      setExecutionResult(res);
      if (res.pending_approval) {
        setEditedArgsJson(JSON.stringify(res.pending_approval.arguments, null, 2));
      }
      refetchHistory();
    } catch {
      // Handled by react-query error state
    }
  };

  const handleRollback = async (checkpointId: string) => {
    if (!threadId) return;
    try {
      await rollbackMutation.mutateAsync({
        tenantId,
        threadId,
        checkpointId,
      });
      refetchHistory();
    } catch {
      // Handled by react-query
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            LangGraph Cyclic Agentic Orchestration
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Stateful multi-agent execution graphs with PostgreSQL state checkpoints, Human-in-the-Loop (HITL) gateways, and time-travel rollbacks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs">
            Milestone 91 • v0.76.0
          </Badge>
          <Badge variant="default" className="bg-emerald-600 text-xs">
            Engine Ready
          </Badge>
        </div>
      </div>

      {/* Tenant Context Bar */}
      <Card>
        <CardContent className="pt-4 flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[240px]">
            <label className="text-xs font-semibold text-muted-foreground">Target Tenant Workspace</label>
            <Input
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              placeholder="e.g. tn_enterprise_01"
              className="mt-1 font-mono text-sm"
            />
          </div>
          <div className="flex-1 min-w-[240px]">
            <label className="text-xs font-semibold text-muted-foreground">Active Thread Session ID</label>
            <div className="flex gap-2 mt-1">
              <Input
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                placeholder="Auto-generated if blank"
                className="font-mono text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setThreadId("");
                  setExecutionResult(null);
                }}
              >
                New
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Grid: Control & Tools vs Live Execution Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Toolbox & Prompt Launchpad */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Tool Registry */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex justify-between items-center">
                <CardTitle className="text-base flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-primary" />
                  Agent Toolbox ({tools.length})
                </CardTitle>
                <span className="text-xs text-muted-foreground">
                  {selectedTools.length > 0 ? `${selectedTools.length} filtered` : "All tools active"}
                </span>
              </div>
              <CardDescription className="text-xs">
                Tools tagged with HITL halt execution at high-risk nodes for human approval.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[260px] overflow-y-auto">
              {loadingTools ? (
                <div className="text-xs text-muted-foreground py-4 text-center">Loading registered tools…</div>
              ) : (
                tools.map((t) => {
                  const isChecked = selectedTools.length === 0 || selectedTools.includes(t.name);
                  return (
                    <div
                      key={t.name}
                      onClick={() => {
                        setSelectedTools((prev) =>
                          prev.includes(t.name) ? prev.filter((x) => x !== t.name) : [...prev, t.name]
                        );
                      }}
                      className={`flex items-center justify-between p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                        isChecked ? "bg-accent/40 border-primary/30" : "opacity-60 border-muted"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold">{t.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {t.requires_approval ? (
                          <Badge
                            variant="destructive"
                            className="text-[10px] px-1.5 py-0 bg-amber-500/20 text-amber-500 border-amber-500/40"
                          >
                            HITL • {t.risk_level.toUpperCase()}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-emerald-500 border-emerald-500/30">
                            AUTO
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Prompt Form */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Task Objective / Goal</CardTitle>
              <CardDescription className="text-xs">
                Launch cyclic reasoning with ReAct tool execution and dynamic state branching.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                rows={3}
                placeholder="e.g. Calculate 18% GST on $4500 and search our refund terms..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="text-sm"
              />

              {/* Quick Preset Buttons */}
              <div className="flex flex-wrap gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => {
                    const p = "Calculate 18% GST on $4500 and search our refund terms";
                    setPrompt(p);
                    handleRun(p);
                  }}
                >
                  Safe: Calc & Search
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs h-7 text-amber-500 border-amber-500/40"
                  onClick={() => {
                    const p = "Delete obsolete document doc_audit_2024 from knowledge base";
                    setPrompt(p);
                    handleRun(p);
                  }}
                >
                  HITL: Delete Document
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs h-7 text-destructive border-destructive/40"
                  onClick={() => {
                    const p = "Revoke expired partner API key 'key_demo_staging'";
                    setPrompt(p);
                    handleRun(p);
                  }}
                >
                  Critical: Revoke API Key
                </Button>
              </div>

              <Button
                className="w-full mt-2"
                onClick={() => handleRun()}
                disabled={executeMutation.isPending || !prompt.trim()}
              >
                {executeMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Orchestrating Graph Steps…
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Agentic Graph
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Time-Travel History Scrubber */}
          {history && history.checkpoints.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <History className="h-4 w-4 text-primary" />
                  Thread Checkpoints ({history.checkpoints.length})
                </CardTitle>
                <CardDescription className="text-xs">
                  Inspect state snapshots and roll back to previous iterations.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 max-h-[220px] overflow-y-auto">
                {history.checkpoints.map((chk) => (
                  <div
                    key={chk.checkpoint_id}
                    className="flex items-center justify-between p-2 rounded-md border bg-muted/20 text-xs"
                  >
                    <div>
                      <span className="font-semibold text-primary">Step {chk.step_index}</span>
                      <span className="text-muted-foreground ml-2 font-mono text-[10px]">[{chk.node_name}]</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs text-amber-500 hover:text-amber-400"
                      onClick={() => handleRollback(chk.checkpoint_id)}
                      disabled={rollbackMutation.isPending}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      Rollback
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Execution Output & HITL Gateway Card */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader className="pb-3 border-b">
              <div className="flex justify-between items-center">
                <CardTitle className="text-base flex items-center gap-2">
                  Live Execution Trace
                  {executionResult && (
                    <Badge
                      variant={
                        executionResult.status === "completed"
                          ? "default"
                          : executionResult.status === "waiting_approval"
                          ? "destructive"
                          : "secondary"
                      }
                      className="text-xs uppercase"
                    >
                      {executionResult.status}
                    </Badge>
                  )}
                </CardTitle>
                {executionResult && (
                  <span className="text-xs text-muted-foreground font-mono">
                    {executionResult.total_steps} steps • {executionResult.execution_time_ms}ms
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              
              {/* HITL Intervention Gateway Card */}
              {executionResult?.pending_approval && (
                <div className="p-4 rounded-xl border border-amber-500 bg-amber-500/10 space-y-3 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
                      <AlertTriangle className="h-5 w-5" />
                      Human Approval Gateway Triggered
                    </div>
                    <Badge variant="destructive" className="bg-amber-600 text-xs">
                      {executionResult.pending_approval.risk_level.toUpperCase()} RISK
                    </Badge>
                  </div>

                  <p className="text-sm font-medium">{executionResult.pending_approval.description}</p>

                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground font-semibold">
                      Proposed Arguments (Editable JSON):
                    </label>
                    <Textarea
                      rows={3}
                      value={editedArgsJson}
                      onChange={(e) => setEditedArgsJson(e.target.value)}
                      className="font-mono text-xs bg-black/40"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs text-muted-foreground font-semibold">
                      Decision Rationale / Feedback:
                    </label>
                    <Input
                      placeholder="Optional notes to pass to the agent..."
                      value={approvalComment}
                      onChange={(e) => setApprovalComment(e.target.value)}
                      className="text-xs"
                    />
                  </div>

                  <div className="flex gap-2 pt-1">
                    <Button
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-500 text-white"
                      onClick={() => handleResume("approve")}
                      disabled={resumeMutation.isPending}
                    >
                      <Check className="h-4 w-4 mr-1.5" />
                      Approve & Resume Graph
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleResume("reject")}
                      disabled={resumeMutation.isPending}
                    >
                      <X className="h-4 w-4 mr-1.5" />
                      Reject Action
                    </Button>
                  </div>
                </div>
              )}

              {/* Iteration Trace Flow */}
              {!executionResult && !executeMutation.isPending && (
                <div className="py-16 text-center text-muted-foreground text-sm">
                  Run a task prompt to visualize cyclic LangGraph reasoning steps.
                </div>
              )}

              {executeMutation.isPending && (
                <div className="py-12 text-center text-primary text-sm flex flex-col items-center gap-2">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                  Cyclic reasoning loop executing…
                </div>
              )}

              {executionResult?.steps.map((step) => (
                <div key={step.step_index} className="p-3.5 rounded-lg border bg-muted/10 space-y-2 text-xs">
                  <div className="flex justify-between items-center text-muted-foreground">
                    <span className="font-bold text-primary">Iteration {step.step_index + 1}</span>
                    <span>{step.tool_calls.length} tool invocation(s)</span>
                  </div>

                  <p className="text-sm font-sans leading-relaxed">
                    <span className="font-semibold text-muted-foreground">Thought:</span> {step.thought}
                  </p>

                  {step.tool_calls.map((call, idx) => (
                    <div key={call.call_id || idx} className="p-2.5 rounded bg-black/30 border space-y-1.5">
                      <div className="flex justify-between items-center font-mono">
                        <span className="text-cyan-400 font-semibold">⚡ {call.tool_name}</span>
                        <code className="text-[10px] text-muted-foreground">{JSON.stringify(call.arguments)}</code>
                      </div>
                      {step.tool_results[idx] && (
                        <div className={`text-[11px] font-mono ${step.tool_results[idx].is_error ? "text-red-400" : "text-emerald-400"}`}>
                          ➔ Observation: {typeof step.tool_results[idx].output === "object" ? JSON.stringify(step.tool_results[idx].output) : String(step.tool_results[idx].output)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}

              {/* Final Synthesis Card */}
              {executionResult?.final_answer && (
                <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 space-y-2">
                  <div className="flex items-center gap-1.5 text-emerald-500 font-semibold text-xs">
                    <CheckCircle2 className="h-4 w-4" />
                    Final Synthesized Answer
                  </div>
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">
                    {executionResult.final_answer}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
