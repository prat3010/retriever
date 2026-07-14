"use client";

import { useState } from "react";
import { usePrompts, useCreatePrompt, useUpdatePrompt, useDeletePrompt, usePreviewPrompt } from "@/hooks/use-prompts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Plus, Eye, Pencil, Trash2, Loader2 } from "lucide-react";

export function TenantPromptsTab({ tenantId }: { tenantId: string }) {
  const { data: prompts, isLoading } = usePrompts(tenantId);
  const createPrompt = useCreatePrompt(tenantId);
  const updatePrompt = useUpdatePrompt(tenantId);
  const deletePrompt = useDeletePrompt(tenantId);
  const previewPrompt = usePreviewPrompt(tenantId);

  const [editDialog, setEditDialog] = useState<{ name: string; content: string; is_system_prompt: boolean } | null>(null);
  const [preview, setPreview] = useState<Array<{ role: string; content: string }> | null>(null);

  async function handleSave() {
    if (!editDialog) return;
    const payload = { name: editDialog.name, content: editDialog.content, is_system_prompt: editDialog.is_system_prompt };
    try {
      if (prompts?.some((p) => p.name === editDialog.name)) {
        await updatePrompt.mutateAsync(payload);
        toast.success("Prompt updated");
      } else {
        await createPrompt.mutateAsync(payload);
        toast.success("Prompt created");
      }
      setEditDialog(null);
    } catch {
      toast.error("Failed to save prompt");
    }
  }

  async function handleDelete(name: string) {
    try {
      await deletePrompt.mutateAsync(name);
      toast.success("Prompt deleted");
    } catch {
      toast.error("Failed to delete prompt");
    }
  }

  async function handlePreview(name: string) {
    try {
      const res = await previewPrompt.mutateAsync({ name, query: "What is the capital of France?" });
      setPreview(res.messages);
    } catch {
      toast.error("Failed to preview prompt");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Dialog open={!!editDialog && !preview} onOpenChange={(open) => { if (!open) setEditDialog(null); }}>
          <DialogTrigger asChild>
            <Button size="sm" onClick={() => setEditDialog({ name: "", content: "", is_system_prompt: true })}>
              <Plus className="mr-2 h-4 w-4" /> New Prompt
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>{editDialog && prompts?.some((p) => p.name === editDialog.name) ? "Edit" : "Create"} Prompt</DialogTitle>
              <DialogDescription>Write or edit a prompt template. Use the preview tab to see rendered output.</DialogDescription>
            </DialogHeader>
            {editDialog && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input value={editDialog.name} onChange={(e) => setEditDialog({ ...editDialog, name: e.target.value })} placeholder="default" />
                </div>
                <div className="space-y-2">
                  <Label>Content</Label>
                  <Textarea className="font-mono text-xs h-48" value={editDialog.content} onChange={(e) => setEditDialog({ ...editDialog, content: e.target.value })} placeholder="You are a helpful assistant..." />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditDialog(null)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!editDialog?.name.trim() || createPrompt.isPending || updatePrompt.isPending}>
                {(createPrompt.isPending || updatePrompt.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {(!prompts || prompts.length === 0) && (
        <p className="text-sm text-muted-foreground text-center py-8">No prompt templates yet.</p>
      )}

      {prompts?.map((p) => (
        <Card key={p.name}>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-medium">{p.name}</CardTitle>
                <Badge variant={p.isSystemPrompt ? "default" : "secondary"}>{p.isSystemPrompt ? "system" : "user"}</Badge>
              </div>
              <div className="flex items-center gap-1">
                <Button size="icon" variant="ghost" onClick={() => handlePreview(p.name)}>
                  <Eye className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" onClick={() => setEditDialog({ name: p.name, content: p.content, is_system_prompt: p.isSystemPrompt })}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" onClick={() => handleDelete(p.name)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="rounded bg-muted p-3 text-xs overflow-x-auto whitespace-pre-wrap max-h-32">
              {p.content.slice(0, 500)}{p.content.length > 500 ? "..." : ""}
            </pre>
          </CardContent>
        </Card>
      ))}

      {preview && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Preview</CardTitle>
              <Button size="sm" variant="ghost" onClick={() => setPreview(null)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {preview.map((m, i) => (
              <div key={i}>
                <span className="text-xs font-semibold text-muted-foreground">{m.role}</span>
                <pre className="rounded bg-muted p-2 text-xs whitespace-pre-wrap mt-1">{m.content}</pre>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
