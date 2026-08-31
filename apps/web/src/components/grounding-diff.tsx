"use client";

import { useState } from "react";
import { ClaimClassification } from "@/hooks/use-hallucinations";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface GroundingDiffProps {
  query?: string;
  answer: string;
  faithfulness?: number;
  hallucinationIndex?: number;
  claims: ClaimClassification[];
  className?: string;
}

export function GroundingDiff({
  query,
  answer,
  faithfulness = 1.0,
  hallucinationIndex = 0.0,
  claims = [],
  className = "",
}: GroundingDiffProps) {
  const [selectedClaimIdx, setSelectedClaimIdx] = useState<number | null>(
    claims.length > 0 ? 0 : null
  );

  const entailedCount = claims.filter((c) => c.status === "entailment").length;
  const contradictedCount = claims.filter((c) => c.status === "contradiction").length;
  const neutralCount = claims.filter((c) => c.status === "neutral").length;
  const totalClaims = claims.length;

  const selectedClaim = selectedClaimIdx !== null && claims[selectedClaimIdx] ? claims[selectedClaimIdx] : null;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Top Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg border bg-card p-3 shadow-sm">
          <span className="text-xs text-muted-foreground">Faithfulness Score</span>
          <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {(faithfulness * 100).toFixed(1)}%
          </div>
        </div>
        <div className="rounded-lg border bg-card p-3 shadow-sm">
          <span className="text-xs text-muted-foreground">Hallucination Index</span>
          <div className="text-xl font-bold text-rose-600 dark:text-rose-400">
            {(hallucinationIndex * 100).toFixed(1)}%
          </div>
        </div>
        <div className="rounded-lg border bg-card p-3 shadow-sm">
          <span className="text-xs text-muted-foreground">Verified Claims</span>
          <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
            {entailedCount} / {totalClaims}
          </div>
        </div>
        <div className="rounded-lg border bg-card p-3 shadow-sm">
          <span className="text-xs text-muted-foreground">Flagged Conflicts</span>
          <div className="text-xl font-bold text-rose-600 dark:text-rose-400">
            {contradictedCount}
          </div>
        </div>
      </div>

      {/* Grounding Score Ratio Bar */}
      {totalClaims > 0 && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Grounding Distribution ({totalClaims} claims evaluated)</span>
            <span>
              🟢 {entailedCount} Entailed &nbsp;|&nbsp; 🟡 {neutralCount} Neutral &nbsp;|&nbsp; 🔴 {contradictedCount} Contradicted
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted flex overflow-hidden">
            <div
              style={{ width: `${(entailedCount / totalClaims) * 100}%` }}
              className="bg-emerald-500 h-full transition-all"
              title={`Entailed: ${entailedCount}`}
            />
            <div
              style={{ width: `${(neutralCount / totalClaims) * 100}%` }}
              className="bg-amber-400 h-full transition-all"
              title={`Neutral: ${neutralCount}`}
            />
            <div
              style={{ width: `${(contradictedCount / totalClaims) * 100}%` }}
              className="bg-rose-500 h-full transition-all"
              title={`Contradicted: ${contradictedCount}`}
            />
          </div>
        </div>
      )}

      {/* Query Banner if provided */}
      {query && (
        <div className="rounded-md bg-muted/50 p-3 border text-sm">
          <span className="font-semibold text-xs text-muted-foreground uppercase tracking-wider block mb-1">
            Prompt Query
          </span>
          <p className="font-mono text-xs">{query}</p>
        </div>
      )}

      {/* Side-by-Side: Sentence Highlights & Claim Inspector Popover */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left / Top: Interactive Sentence Highlighting */}
        <div className="lg:col-span-7 space-y-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Claim-by-Claim Interactive Grounding</CardTitle>
              <CardDescription className="text-xs">
                Click any highlighted sentence to inspect directional NLI entailment probabilities and source premise citations.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {claims.length === 0 ? (
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{answer}</p>
              ) : (
                <div className="leading-relaxed text-sm space-y-1">
                  {claims.map((item, idx) => {
                    const isSelected = selectedClaimIdx === idx;
                    let styleClass = "bg-muted/40 text-foreground border-transparent";
                    let badgeLabel = "Neutral";
                    let badgeColor = "border-amber-500 text-amber-500";

                    if (item.status === "entailment") {
                      styleClass = isSelected
                        ? "bg-emerald-500/20 text-emerald-950 dark:text-emerald-200 border-b-2 border-emerald-500 font-medium"
                        : "bg-emerald-500/10 text-emerald-900 dark:text-emerald-300 border-b-2 border-emerald-500/60 hover:bg-emerald-500/20";
                      badgeLabel = "Entailed";
                      badgeColor = "border-emerald-500 text-emerald-600 dark:text-emerald-400";
                    } else if (item.status === "contradiction") {
                      styleClass = isSelected
                        ? "bg-rose-500/20 text-rose-950 dark:text-rose-200 border-b-2 border-rose-500 font-medium"
                        : "bg-rose-500/10 text-rose-900 dark:text-rose-300 border-b-2 border-rose-500/60 hover:bg-rose-500/20";
                      badgeLabel = "Contradiction";
                      badgeColor = "border-rose-500 text-rose-600 dark:text-rose-400";
                    } else {
                      styleClass = isSelected
                        ? "bg-amber-500/20 text-amber-950 dark:text-amber-200 border-b-2 border-amber-500 font-medium"
                        : "bg-amber-500/10 text-amber-900 dark:text-amber-300 border-b-2 border-amber-500/60 hover:bg-amber-500/20";
                    }

                    return (
                      <span
                        key={idx}
                        onClick={() => setSelectedClaimIdx(idx)}
                        className={`inline-block px-1.5 py-0.5 rounded cursor-pointer transition-all mr-1 my-0.5 ${styleClass}`}
                      >
                        {item.claim}{" "}
                        <span className={`text-[10px] px-1 py-0.2 rounded border font-mono ${badgeColor}`}>
                          [{badgeLabel}]
                        </span>
                      </span>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right / Bottom: Selected Claim Citation & NLI Calibrated Inspector */}
        <div className="lg:col-span-5 space-y-3">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Claim Verification Details</CardTitle>
                {selectedClaim && (
                  <Badge
                    variant="outline"
                    className={
                      selectedClaim.status === "entailment"
                        ? "border-emerald-500 text-emerald-600 dark:text-emerald-400"
                        : selectedClaim.status === "contradiction"
                        ? "border-rose-500 text-rose-600 dark:text-rose-400"
                        : "border-amber-500 text-amber-600 dark:text-amber-400"
                    }
                  >
                    {selectedClaim.status === "entailment"
                      ? "✅ Grounded in Context"
                      : selectedClaim.status === "contradiction"
                      ? "⚠️ Direct Contradiction"
                      : "🟡 Unsupported / Neutral"}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {!selectedClaim ? (
                <div className="py-8 text-center text-muted-foreground">
                  Select any sentence on the left to inspect its source premise grounding.
                </div>
              ) : (
                <>
                  <div>
                    <span className="font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                      Target Claim Sentence ({selectedClaimIdx! + 1} of {claims.length})
                    </span>
                    <div className="p-2.5 rounded bg-muted/60 font-mono text-xs leading-relaxed border">
                      "{selectedClaim.claim}"
                    </div>
                  </div>

                  {/* NLI Probabilities Breakdown */}
                  <div className="space-y-1.5">
                    <span className="font-semibold text-muted-foreground uppercase tracking-wider block">
                      NLI Cross-Encoder Probabilities
                    </span>
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="flex justify-between items-center">
                        <span className="text-emerald-600 dark:text-emerald-400">Entailment</span>
                        <span>{(selectedClaim.entailment_prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full"
                          style={{ width: `${selectedClaim.entailment_prob * 100}%` }}
                        />
                      </div>

                      <div className="flex justify-between items-center pt-1">
                        <span className="text-amber-600 dark:text-amber-400">Neutral</span>
                        <span>{(selectedClaim.neutral_prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="bg-amber-400 h-full"
                          style={{ width: `${selectedClaim.neutral_prob * 100}%` }}
                        />
                      </div>

                      <div className="flex justify-between items-center pt-1">
                        <span className="text-rose-600 dark:text-rose-400">Contradiction</span>
                        <span>{(selectedClaim.contradiction_prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="bg-rose-500 h-full"
                          style={{ width: `${selectedClaim.contradiction_prob * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Matched Source Context Premise */}
                  <div>
                    <span className="font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                      Matched Source Premise Citation
                    </span>
                    {selectedClaim.premise ? (
                      <div className="p-2.5 rounded bg-muted/60 font-mono text-xs leading-relaxed border border-emerald-500/30">
                        {selectedClaim.premise}
                      </div>
                    ) : (
                      <div className="p-2.5 rounded bg-muted/30 font-mono text-xs text-muted-foreground italic border">
                        No grounding source chunk found in retrieved context for this claim.
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
