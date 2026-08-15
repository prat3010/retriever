"use client";

import { useHallucinationSummary } from "@/hooks/use-hallucinations";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

interface TenantHallucinationsTabProps {
  tenantId: string;
}

export function TenantHallucinationsTab({ tenantId }: TenantHallucinationsTabProps) {
  const { data, isLoading } = useHallucinationSummary(tenantId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const avgFaithfulness = data ? (data.avg_faithfulness * 100).toFixed(1) : "0.0";
  const avgRelevance = data ? (data.avg_context_relevance * 100).toFixed(1) : "0.0";

  return (
    <div className="space-y-6">
      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Live Evaluations</CardDescription>
            <CardTitle className="text-2xl">{data?.total_evaluations ?? 0}</CardTitle>
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
            <CardDescription>Context Relevance</CardDescription>
            <CardTitle className="text-2xl text-blue-600 dark:text-blue-400">{avgRelevance}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Flagged Hallucinations</CardDescription>
            <CardTitle className="text-2xl text-amber-600 dark:text-amber-400">{data?.unfaithful_count ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Evaluations Table */}
      <Card>
        <CardHeader>
          <CardTitle>Online Production Evaluation Log</CardTitle>
          <CardDescription>Real-time faithfulness and context relevance scores on live chat response streams.</CardDescription>
        </CardHeader>
        <CardContent>
          {!data?.evaluations || data.evaluations.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No evaluation records found for this tenant yet.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Session ID</TableHead>
                  <TableHead>Faithfulness</TableHead>
                  <TableHead>Relevance</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.evaluations.map((item) => (
                  <TableRow key={item.evaluation_id}>
                    <TableCell className="font-mono text-xs">{new Date(item.created_at).toLocaleString()}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{item.session_id.slice(0, 8)}...</TableCell>
                    <TableCell className="font-mono font-medium">{(item.faithfulness_score * 100).toFixed(1)}%</TableCell>
                    <TableCell className="font-mono font-medium">{(item.context_relevance_score * 100).toFixed(1)}%</TableCell>
                    <TableCell>
                      {item.is_hallucination ? (
                        <Badge variant="destructive">⚠️ Hallucination</Badge>
                      ) : (
                        <Badge variant="outline" className="text-emerald-600 border-emerald-500">✅ Faithful</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
