"use client";

import { useState } from "react";
import { useRlmAnalysisMutation, useConsensusMutation, RlmAnalysisResult, ConsensusResult } from "@/hooks/use-cognitive";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Brain, Terminal, ShieldCheck, Play, Loader2, Sparkles, CheckCircle2, AlertCircle, Clock } from "lucide-react";

interface TenantCognitiveLabTabProps {
  tenantId: string;
}

export function TenantCognitiveLabTab({ tenantId }: TenantCognitiveLabTabProps) {
  const [subTab, setSubTab] = useState<"rlm" | "consensus">("rlm");

  // RLM State
  const [rlmPrompt, setRlmPrompt] = useState<string>(
    "Execute an empirical multi-step audit of the ingested knowledge base, analyze deliverable scopes, and calculate budget allocation."
  );
  const [maxDepth, setMaxDepth] = useState<number>(3);
  const [rlmResult, setRlmResult] = useState<RlmAnalysisResult | null>(null);
  const rlmMutation = useRlmAnalysisMutation(tenantId);

  // Consensus State
  const [consensusPrompt, setConsensusPrompt] = useState<string>(
    "Explain the security guarantees and tenant data isolation boundaries in our RAG architecture."
  );
  const [generatorModel, setGeneratorModel] = useState<string>("gemini");
  const [criticModel, setCriticModel] = useState<string>("openai");
  const [reflectionRounds, setReflectionRounds] = useState<number>(2);
  const [consensusResult, setConsensusResult] = useState<ConsensusResult | null>(null);
  const consensusMutation = useConsensusMutation(tenantId);

  const handleRunRlm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rlmPrompt.trim()) return;

    try {
      const res = await rlmMutation.mutateAsync({
        prompt: rlmPrompt.trim(),
        max_depth: maxDepth,
      });
      setRlmResult(res);
      toast.success(`RLM analysis finished in ${res.execution_time_ms.toFixed(0)}ms with ${res.subcalls_count} sub-calls!`);
    } catch (err: any) {
      toast.error(err.message || "RLM execution failed.");
    }
  };

  const handleRunConsensus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consensusPrompt.trim()) return;

    try {
      const res = await consensusMutation.mutateAsync({
        prompt: consensusPrompt.trim(),
        generator_provider_name: generatorModel,
        critic_provider_name: criticModel,
        max_reflection_rounds: reflectionRounds,
      });
      setConsensusResult(res);
      toast.success(`Consensus approved on Round ${res.approved_on_round}!`);
    } catch (err: any) {
      toast.error(err.message || "Consensus execution failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Brain className="h-6 w-6 text-primary" />
            <span>Cognitive Labs & Deep Analytical Reasoning</span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Test Recursive Language Modeling (RLM) with Python REPL sandboxing and Multi-Agent Generator-Critic Consensus.
          </p>
        </div>

        <Tabs value={subTab} onValueChange={(v: string) => setSubTab(v as "rlm" | "consensus")}>
          <TabsList>
            <TabsTrigger value="rlm">🐍 RLM Python REPL</TabsTrigger>
            <TabsTrigger value="consensus">🤝 Multi-Agent Consensus</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* SUB-TAB 1: RLM Python REPL */}
      {subTab === "rlm" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Terminal className="h-5 w-5 text-emerald-500" />
                <span>Recursive Language Model (RLM) Analytical Engine</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Executes recursive decomposition, context minimization, and programmatic Python REPL reasoning loops to solve complex analytical problems.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRunRlm} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="rlm-prompt">Analytical Objective / Prompt</Label>
                  <Textarea
                    id="rlm-prompt"
                    rows={3}
                    value={rlmPrompt}
                    onChange={(e) => setRlmPrompt(e.target.value)}
                    placeholder="Enter analytical goal..."
                    required
                  />
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <Label htmlFor="rlm-depth" className="text-xs">
                      Max Recursion Depth:
                    </Label>
                    <Select value={String(maxDepth)} onValueChange={(v) => setMaxDepth(Number(v))}>
                      <SelectTrigger id="rlm-depth" className="w-28 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 (Single Pass)</SelectItem>
                        <SelectItem value="2">2 Passes</SelectItem>
                        <SelectItem value="3">3 Passes (Recommended)</SelectItem>
                        <SelectItem value="5">5 Passes (Deep)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button type="submit" disabled={rlmMutation.isPending || !rlmPrompt.trim()}>
                    {rlmMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Running REPL Analysis Loop...
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Execute RLM Engine
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* RLM Results Display */}
          {rlmResult && (
            <div className="space-y-4">
              <Card className="border-emerald-500/30">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-base text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                      <Sparkles className="h-4 w-4" />
                      <span>Synthesized Analytical Summary</span>
                    </CardTitle>
                    <div className="flex gap-2">
                      <Badge variant="outline" className="text-xs font-mono">
                        <Clock className="h-3 w-3 mr-1" />
                        {rlmResult.execution_time_ms.toFixed(0)} ms
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {rlmResult.subcalls_count} Sub-calls
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{rlmResult.analysis_summary}</p>
                </CardContent>
              </Card>

              {/* Code Executions Trace */}
              {rlmResult.code_executions && rlmResult.code_executions.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-mono flex items-center gap-2">
                      <Terminal className="h-4 w-4 text-primary" />
                      <span>Sandboxed Python REPL Trace Logs</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {rlmResult.code_executions.map((exec, idx) => (
                      <div key={idx} className="p-3 bg-muted/60 rounded-lg border font-mono text-xs space-y-2">
                        <div className="flex justify-between text-muted-foreground text-[10px]">
                          <span>EXECUTION TURN #{idx + 1}</span>
                          <span>{exec.execution_time_ms ? `${exec.execution_time_ms.toFixed(1)} ms` : "Instant"}</span>
                        </div>
                        {exec.script && (
                          <pre className="p-2 bg-background/80 rounded border overflow-x-auto text-blue-600 dark:text-blue-400">
                            <code>{exec.script}</code>
                          </pre>
                        )}
                        {exec.output && (
                          <div className="text-emerald-600 dark:text-emerald-400 text-xs">
                            <strong>STDOUT:</strong> {exec.output}
                          </div>
                        )}
                        {exec.is_error && (
                          <div className="text-rose-500 text-xs">
                            <strong>ERROR:</strong> {exec.error_message}
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 2: Multi-Agent Consensus */}
      {subTab === "consensus" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-blue-500" />
                <span>Generator vs. Critic Multi-Agent Consensus Calibration</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Pair a Generator LLM with an adversarial Critic/Auditor LLM. The Critic continuously fact-checks claims against retrieved sources until consensus is reached.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRunConsensus} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cons-prompt">Query / Task for Consensus Verification</Label>
                  <Textarea
                    id="cons-prompt"
                    rows={3}
                    value={consensusPrompt}
                    onChange={(e) => setConsensusPrompt(e.target.value)}
                    placeholder="Enter query..."
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="gen-model" className="text-xs">
                      Generator Agent Model
                    </Label>
                    <Select value={generatorModel} onValueChange={setGeneratorModel}>
                      <SelectTrigger id="gen-model" className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gemini">Google Gemini 2.5 Flash</SelectItem>
                        <SelectItem value="openai">OpenAI GPT-4o-mini</SelectItem>
                        <SelectItem value="anthropic">Anthropic Claude 3.5 Haiku</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="crit-model" className="text-xs">
                      Critic / Auditor Agent Model
                    </Label>
                    <Select value={criticModel} onValueChange={setCriticModel}>
                      <SelectTrigger id="crit-model" className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="openai">OpenAI GPT-4o (Strict Auditor)</SelectItem>
                        <SelectItem value="gemini">Google Gemini 2.5 Pro</SelectItem>
                        <SelectItem value="anthropic">Anthropic Claude 3.5 Sonnet</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="ref-rounds" className="text-xs">
                      Max Reflection Passes
                    </Label>
                    <Select value={String(reflectionRounds)} onValueChange={(v) => setReflectionRounds(Number(v))}>
                      <SelectTrigger id="ref-rounds" className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 Pass</SelectItem>
                        <SelectItem value="2">2 Passes (Standard)</SelectItem>
                        <SelectItem value="3">3 Passes (High Precision)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button type="submit" disabled={consensusMutation.isPending || !consensusPrompt.trim()}>
                    {consensusMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Executing Multi-Agent Reflection Loop...
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Run Consensus Loop
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Consensus Results Display */}
          {consensusResult && (
            <div className="space-y-4">
              <Card className="border-blue-500/30">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-base text-blue-600 dark:text-blue-400 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Consensus Verified Response</span>
                    </CardTitle>
                    <div className="flex gap-2">
                      <Badge className="bg-emerald-600 text-white text-xs">
                        Approved on Round {consensusResult.approved_on_round}
                      </Badge>
                      <Badge variant="outline" className="text-xs font-mono">
                        {consensusResult.execution_time_ms.toFixed(0)} ms
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{consensusResult.final_response}</p>
                </CardContent>
              </Card>

              {/* Reflection History Breakdown */}
              {consensusResult.reflection_history && consensusResult.reflection_history.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Critique & Revision Iteration History</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {consensusResult.reflection_history.map((hist, idx) => (
                      <div key={idx} className="p-3 bg-muted/60 rounded-lg border text-xs space-y-2">
                        <div className="flex justify-between items-center font-mono">
                          <span className="font-semibold">ROUND #{hist.round || idx + 1}</span>
                          <Badge variant={hist.critic_approved ? "default" : "destructive"}>
                            Score: {(hist.critique_score * 100).toFixed(0)}% — {hist.critic_approved ? "Approved" : "Revision Required"}
                          </Badge>
                        </div>
                        {hist.critique_feedback && (
                          <div className="text-muted-foreground">
                            <strong>Critic Feedback:</strong> {hist.critique_feedback}
                          </div>
                        )}
                        {hist.unsupported_claims && hist.unsupported_claims.length > 0 && (
                          <div className="text-rose-500">
                            <strong>Flagged Claims:</strong> {hist.unsupported_claims.join("; ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
