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
import { Plus, Eye, Pencil, Trash2, Loader2, Lock, Unlock } from "lucide-react";
import type { PromptTemplate } from "@/hooks/use-prompts";

export function TenantPromptsTab({ tenantId }: { tenantId: string }) {
  const { data: prompts, isLoading } = usePrompts(tenantId);
  const createPrompt = useCreatePrompt(tenantId);
  const updatePrompt = useUpdatePrompt(tenantId);
  const deletePrompt = useDeletePrompt(tenantId);
  const previewPrompt = usePreviewPrompt(tenantId);

  const [editDialog, setEditDialog] = useState<{
    name: string;
    content: string;
    is_system_prompt: boolean;
    is_locked: boolean;
  } | null>(null);
  const [preview, setPreview] = useState<Array<{ role: string; content: string }> | null>(null);

  async function handleSave() {
    if (!editDialog) return;
    const payload = {
      name: editDialog.name,
      content: editDialog.content,
      is_system_prompt: editDialog.is_system_prompt,
      is_locked: editDialog.is_locked,
    };
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

  async function handleToggleLock(prompt: PromptTemplate) {
    try {
      await updatePrompt.mutateAsync({
        name: prompt.name,
        content: prompt.content,
        is_system_prompt: prompt.isSystemPrompt,
        is_locked: !prompt.isLocked,
      });
      toast.success(prompt.isLocked ? "Prompt unlocked for tenant edits" : "Prompt locked by admin policy");
    } catch {
      toast.error("Failed to update lock status");
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
            <Button size="sm" onClick={() => setEditDialog({ name: "", content: "", is_system_prompt: true, is_locked: false })} aria-label="Create new prompt template">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" /> New Prompt
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
                  <Label htmlFor="prompt-name">Name</Label>
                  <Input id="prompt-name" value={editDialog.name} onChange={(e) => setEditDialog({ ...editDialog, name: e.target.value })} placeholder="default" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prompt-content">Content</Label>
                  <Textarea id="prompt-content" className="font-mono text-xs h-48" value={editDialog.content} onChange={(e) => setEditDialog({ ...editDialog, content: e.target.value })} placeholder="You are a helpful assistant..." />
                </div>
                <div className="flex items-center space-x-2 pt-1">
                  <input
                    type="checkbox"
                    id="prompt-locked"
                    checked={editDialog.is_locked}
                    onChange={(e) => setEditDialog({ ...editDialog, is_locked: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 cursor-pointer"
                  />
                  <Label htmlFor="prompt-locked" className="text-xs font-medium cursor-pointer">
                    🔒 Lock Master Prompt (Prevent Tenant API Modification)
                  </Label>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditDialog(null)}>Cancel</Button>
              <Button onClick={handleSave} disabled={!editDialog?.name.trim() || createPrompt.isPending || updatePrompt.isPending}>
                {(createPrompt.isPending || updatePrompt.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
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
                {p.isLocked && (
                  <Badge variant="destructive" className="text-xs">
                    🔒 Locked
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => handleToggleLock(p)}
                  aria-label={p.isLocked ? `Unlock prompt ${p.name}` : `Lock prompt ${p.name}`}
                  title={p.isLocked ? "Unlock prompt for tenant" : "Lock prompt (admin policy)"}
                >
                  {p.isLocked ? <Lock className="h-4 w-4 text-amber-500" /> : <Unlock className="h-4 w-4 text-muted-foreground" />}
                </Button>
                <Button size="icon" variant="ghost" onClick={() => handlePreview(p.name)} aria-label={`Preview prompt template ${p.name}`}>
                  <Eye className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() =>
                    setEditDialog({
                      name: p.name,
                      content: p.content,
                      is_system_prompt: p.isSystemPrompt,
                      is_locked: !!p.isLocked,
                    })
                  }
                  aria-label={`Edit prompt template ${p.name}`}
                >
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button size="icon" variant="ghost" onClick={() => handleDelete(p.name)} aria-label={`Delete prompt template ${p.name}`}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
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
