"use client";

import { useState } from "react";
import { useLoraAdapters, useTrainLoraAdapter, useActivateLoraAdapter, LoraAdapter } from "@/hooks/use-lora";
import { useConfig } from "@/hooks/use-config";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Dna, Sparkles, CheckCircle2, PlayCircle, Loader2, ArrowRight } from "lucide-react";

interface TenantLoraTabProps {
  tenantId: string;
}

export function TenantLoraTab({ tenantId }: TenantLoraTabProps) {
  const { data: adapters, isLoading: isAdaptersLoading } = useLoraAdapters(tenantId);
  const { data: config, isLoading: isConfigLoading } = useConfig(tenantId);
  const trainMutation = useTrainLoraAdapter(tenantId);
  const activateMutation = useActivateLoraAdapter(tenantId);

  const [isTrainOpen, setIsTrainOpen] = useState(false);
  const [adapterName, setAdapterName] = useState("Enterprise SOW & Architecture Adapter");
  const [domainTag, setDomainTag] = useState("software_architecture");
  const [loraRank, setLoraRank] = useState(8);
  const [epochs, setEpochs] = useState(15);
  const [learningRate, setLearningRate] = useState(0.001);

  const activeAdapterId = config?.retrieval_settings?.active_lora_adapter || null;
  const activeAdapter = adapters?.find((a) => a.adapter_id === activeAdapterId) || null;

  const handleTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adapterName.trim()) return;

    try {
      const res = await trainMutation.mutateAsync({
        name: adapterName.trim(),
        domain_tag: domainTag.trim() || "general",
        rank: Number(loraRank),
        epochs: Number(epochs),
        learning_rate: Number(learningRate),
      });
      toast.success(`Adapter '${res.name}' trained successfully with loss ${res.loss_score.toFixed(4)}!`);
      setIsTrainOpen(false);
    } catch (err: any) {
      toast.error(err.message || "Failed to train LoRA adapter.");
    }
  };

  const handleActivate = async (adapterId: string) => {
    try {
      await activateMutation.mutateAsync(adapterId);
      toast.success("Active LoRA adapter switched.");
    } catch (err: any) {
      toast.error(err.message || "Failed to activate adapter.");
    }
  };

  if (isAdaptersLoading || isConfigLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const adapterList = adapters || [];
  const minLoss = adapterList.reduce((min, a) => (a.loss_score !== null && a.loss_score < min ? a.loss_score : min), 999.0);

  return (
    <div className="space-y-6">
      {/* Top Metric Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Trained Domain Adapters</CardDescription>
            <CardTitle className="text-2xl font-bold flex items-center gap-2">
              <Dna className="h-5 w-5 text-indigo-500" />
              {adapterList.length}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Serving Model</CardDescription>
            <CardTitle className="text-base font-semibold truncate text-emerald-600 dark:text-emerald-400">
              {activeAdapter ? `${activeAdapter.name} (r=${activeAdapter.rank})` : "Base nomic-embed-text"}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Best Empirical Loss</CardDescription>
            <CardTitle className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {minLoss < 900 ? minLoss.toFixed(4) : "--"}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Residual Projection</CardDescription>
            <CardTitle className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {activeAdapter ? `Rank ${activeAdapter.rank}` : "Identity Matrix"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Action Bar & Training Modal */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span>🧬 Low-Rank Adaptation (LoRA) Fine-Tuning Hub</span>
              <Badge variant="outline" className="text-xs font-mono">
                W_eff = W_base + (B · A) · (α / r)
              </Badge>
            </CardTitle>
            <CardDescription>
              Fine-tune contrastive projection matrices directly over tenant document pairs to sharpen domain-specific embeddings.
            </CardDescription>
          </div>

          <Dialog open={isTrainOpen} onOpenChange={setIsTrainOpen}>
            <DialogTrigger asChild>
              <Button className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Train New Adapter
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[480px]">
              <DialogHeader>
                <DialogTitle>Fine-Tune LoRA Embedding Layer</DialogTitle>
                <DialogDescription>
                  Calibrate low-rank projection weights over tenant contrastive pairs without modifying base embedding model weights.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleTrain} className="space-y-4 pt-2">
                <div className="space-y-2">
                  <Label htmlFor="adapter-name">Adapter Name</Label>
                  <Input
                    id="adapter-name"
                    value={adapterName}
                    onChange={(e) => setAdapterName(e.target.value)}
                    placeholder="e.g. Legal Contract Terminology Adapter"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="domain-tag">Domain Tag</Label>
                    <Input
                      id="domain-tag"
                      value={domainTag}
                      onChange={(e) => setDomainTag(e.target.value)}
                      placeholder="e.g. legal_tech"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="lora-rank">LoRA Rank (r)</Label>
                    <Select value={String(loraRank)} onValueChange={(v) => setLoraRank(Number(v))}>
                      <SelectTrigger id="lora-rank">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="4">r = 4 (Fastest, 32KB)</SelectItem>
                        <SelectItem value="8">r = 8 (Recommended)</SelectItem>
                        <SelectItem value="16">r = 16 (High Capacity)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="epochs">Epochs</Label>
                    <Input
                      id="epochs"
                      type="number"
                      min={1}
                      max={50}
                      value={epochs}
                      onChange={(e) => setEpochs(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lr">Learning Rate</Label>
                    <Input
                      id="lr"
                      type="number"
                      step={0.0001}
                      min={0.0001}
                      max={0.1}
                      value={learningRate}
                      onChange={(e) => setLearningRate(Number(e.target.value))}
                    />
                  </div>
                </div>

                <Button type="submit" className="w-full" disabled={trainMutation.isPending}>
                  {trainMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Calibrating LoRA Projection Layer...
                    </>
                  ) : (
                    "Launch LoRA Calibration Pass"
                  )}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </CardHeader>
        <CardContent>
          {adapterList.length === 0 ? (
            <div className="text-center py-10 space-y-3">
              <Dna className="h-10 w-10 text-muted-foreground mx-auto opacity-50" />
              <p className="text-sm font-medium">No custom LoRA adapters calibrated for this tenant yet.</p>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Retriever is currently serving zero-residual embeddings directly from the base local model.
                Click &quot;Train New Adapter&quot; to calibrate custom projection layers.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Adapter Name</TableHead>
                  <TableHead>Domain Tag</TableHead>
                  <TableHead>Rank (r)</TableHead>
                  <TableHead>Loss Score</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {adapterList.map((ad: LoraAdapter) => {
                  const isActive = ad.adapter_id === activeAdapterId;
                  return (
                    <TableRow key={ad.adapter_id}>
                      <TableCell className="font-medium flex items-center gap-2">
                        <Dna className="h-4 w-4 text-indigo-400" />
                        {ad.name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{ad.domain_tag}</Badge>
                      </TableCell>
                      <TableCell className="font-mono">r = {ad.rank}</TableCell>
                      <TableCell className="font-mono text-emerald-600 dark:text-emerald-400">
                        {ad.loss_score !== null ? ad.loss_score.toFixed(4) : "--"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(ad.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {isActive ? (
                          <Badge className="bg-emerald-600 text-white flex items-center gap-1 w-fit">
                            <CheckCircle2 className="h-3 w-3" /> Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-muted-foreground">
                            Standby
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant={isActive ? "outline" : "default"}
                          disabled={isActive || activateMutation.isPending}
                          onClick={() => handleActivate(ad.adapter_id)}
                        >
                          {isActive ? "Active Serving" : "Deploy Adapter"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
