"use client";

import { useState } from "react";
import {
  useOnlineEvaluationSummary,
  useOnlineEvaluationLogs,
  OnlineEvaluationLog,
} from "@/hooks/use-hallucinations";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GroundingDiff } from "@/components/grounding-diff";

interface TenantHallucinationsTabProps {
  tenantId: string;
}

export function TenantHallucinationsTab({ tenantId }: TenantHallucinationsTabProps) {
  const { data: summary, isLoading: isSummaryLoading } = useOnlineEvaluationSummary(tenantId);
  const { data: logsData, isLoading: isLogsLoading } = useOnlineEvaluationLogs(tenantId, 50, 0);
  const [inspectingLog, setInspectingLog] = useState<OnlineEvaluationLog | null>(null);

  if (isSummaryLoading || isLogsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const avgFaithfulness = summary ? (summary.avg_faithfulness * 100).toFixed(1) : "0.0";
  const avgPrecision = summary ? (summary.avg_context_precision * 100).toFixed(1) : "0.0";
  const avgHallucination = summary ? (summary.avg_hallucination_index * 100).toFixed(1) : "0.0";
  const totalAlerts = summary?.total_alerts ?? 0;

  const logs = logsData?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Live Evaluations</CardDescription>
            <CardTitle className="text-2xl">{summary?.total_evaluations ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Faithfulness Score</CardDescription>
            <CardTitle className="text-2xl text-emerald-600 dark:text-emerald-400">{avgFaithfulness}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Context Precision</CardDescription>
            <CardTitle className="text-2xl text-blue-600 dark:text-blue-400">{avgPrecision}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Hallucination Incidents</CardDescription>
            <CardTitle className="text-2xl text-rose-600 dark:text-rose-400">{totalAlerts}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Evaluations Table */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Online Production Evaluation Log</CardTitle>
              <CardDescription>
                Real-time claim entailment, precision, and faithfulness scores evaluated against source documents.
              </CardDescription>
            </div>
            <Badge variant="outline" className="font-mono text-xs">
              Avg Hallucination Rate: {avgHallucination}%
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground space-y-2">
              <p className="text-base font-medium">No evaluation records found for this tenant yet.</p>
              <p className="text-xs">
                Inference runs with online evaluation enabled will automatically appear here with claim grounding breakdowns.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Query / Session</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Precision</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((item) => (
                  <TableRow
                    key={item.eval_id}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => setInspectingLog(item)}
                  >
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="max-w-[300px]">
                      <div className="font-medium text-xs truncate">{item.query || "(Direct message)"}</div>
                      <div className="font-mono text-[10px] text-muted-foreground">
                        Session: {item.session_id ? `${item.session_id.slice(0, 8)}...` : "n/a"}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono font-medium text-xs">
                      {(item.faithfulness * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell className="font-mono font-medium text-xs">
                      {(item.context_precision * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell>
                      {item.is_alert || item.hallucination_index > 0.3 ? (
                        <Badge variant="destructive" className="text-[11px]">
                          ⚠️ Hallucination ({(item.hallucination_index * 100).toFixed(0)}%)
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-emerald-600 border-emerald-500 text-[11px]">
                          ✅ Faithful
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs text-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          setInspectingLog(item);
                        }}
                      >
                        Inspect Claims →
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Grounding Diff Modal */}
      <Dialog open={!!inspectingLog} onOpenChange={(open) => !open && setInspectingLog(null)}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <span>Claim-by-Claim Visual Grounding Inspector</span>
              {inspectingLog && (
                <Badge variant="outline" className="font-mono text-xs">
                  Eval ID: {inspectingLog.eval_id.slice(0, 8)}...
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Natural Language Inference (NLI) sentence verification against retrieved context chunks.
            </DialogDescription>
          </DialogHeader>

          {inspectingLog && (
            <div className="pt-2">
              <GroundingDiff
                query={inspectingLog.query}
                answer={inspectingLog.answer}
                faithfulness={inspectingLog.faithfulness}
                hallucinationIndex={inspectingLog.hallucination_index}
                claims={inspectingLog.claims || []}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

