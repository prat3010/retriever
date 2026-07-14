"use client";

import { useApiKeys, useCreateApiKey, useRevokeApiKey, type CreatedApiKey } from "@/hooks/use-api-keys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useState } from "react";

interface Props {
  tenantId: string;
}

export function ApiKeysTab({ tenantId }: Props) {
  const { data: keys, isLoading } = useApiKeys(tenantId);
  const createKey = useCreateApiKey(tenantId);
  const revokeKey = useRevokeApiKey(tenantId);

  const [createOpen, setCreateOpen] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [keyRole, setKeyRole] = useState<"admin" | "client">("client");
  const [expiresInDays, setExpiresInDays] = useState("");
  const [newKey, setNewKey] = useState<CreatedApiKey | null>(null);

  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [revokeOpen, setRevokeOpen] = useState(false);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!keyName.trim()) return;
    createKey.mutate(
      {
        name: keyName.trim(),
        role: keyRole,
        expires_in_days: expiresInDays ? Number(expiresInDays) : undefined,
      },
      {
        onSuccess: (data) => {
          setNewKey(data);
          setCreateOpen(false);
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  function handleRevoke(keyId: string) {
    revokeKey.mutate(keyId, {
      onSuccess: () => {
        toast.success("API key revoked");
        setRevokeOpen(false);
        setRevokeId(null);
      },
      onError: () => toast.error("Failed to revoke key"),
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">API Keys</h3>
        <Dialog
          open={createOpen}
          onOpenChange={(open) => { setCreateOpen(open); if (!open) setNewKey(null); }}
        >
          <DialogTrigger asChild>
            <Button>Generate Key</Button>
          </DialogTrigger>
          <DialogContent>
            {newKey ? (
              <div className="space-y-4 py-4">
                <DialogHeader>
                  <DialogTitle>Key Created</DialogTitle>
                </DialogHeader>
                <p className="text-sm text-muted-foreground">
                  Copy this key now — you won&apos;t be able to see it again.
                </p>
                <div className="rounded-md bg-muted p-3">
                  <code className="break-all text-sm">{newKey.apiKey}</code>
                </div>
                <Button
                  className="w-full"
                  onClick={() => {
                    navigator.clipboard.writeText(newKey.apiKey);
                    toast.success("Copied to clipboard");
                  }}
                >
                  Copy to Clipboard
                </Button>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setNewKey(null)}>
                    Done
                  </Button>
                </DialogFooter>
              </div>
            ) : (
              <form onSubmit={handleCreate}>
                <DialogHeader>
                  <DialogTitle>Generate API Key</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="keyName">Name *</Label>
                    <Input
                      id="keyName"
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      placeholder="my-integration-key"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="keyRole">Role</Label>
                    <Select
                      value={keyRole}
                      onValueChange={(v) => setKeyRole(v as "admin" | "client")}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="client">Client</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="expiresIn">Expires in (days, optional)</Label>
                    <Input
                      id="expiresIn"
                      type="number"
                      min={1}
                      value={expiresInDays}
                      onChange={(e) => setExpiresInDays(e.target.value)}
                      placeholder="90"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button type="submit" disabled={createKey.isPending}>
                    {createKey.isPending ? "Generating..." : "Generate"}
                  </Button>
                </DialogFooter>
              </form>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Prefix</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead className="w-20">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {keys?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No API keys found
                </TableCell>
              </TableRow>
            )}
            {keys?.map((key) => (
              <TableRow key={key.keyId}>
                <TableCell className="font-medium">{key.name}</TableCell>
                <TableCell className="font-mono text-sm text-muted-foreground">
                  {key.prefix}...
                </TableCell>
                <TableCell>
                  <Badge variant={key.role === "admin" ? "default" : "secondary"}>
                    {key.role}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={key.status === "active" ? "default" : "secondary"}>
                    {key.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {key.expiresAt
                    ? new Date(key.expiresAt).toLocaleDateString()
                    : "Never"}
                </TableCell>
                <TableCell>
                  {key.status === "active" && (
                    <Dialog
                      open={revokeOpen && revokeId === key.keyId}
                      onOpenChange={(open) => { setRevokeOpen(open); setRevokeId(key.keyId); }}
                    >
                      <DialogTrigger asChild>
                        <Button variant="destructive" size="sm">Revoke</Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Revoke API key?</DialogTitle>
                          <DialogDescription>
                          This will immediately invalidate &quot;{key.name}&quot;.
                          Any services using this key will lose access.
                          </DialogDescription>
                        </DialogHeader>
                        <DialogFooter>
                          <Button variant="outline" onClick={() => setRevokeOpen(false)}>
                            Cancel
                          </Button>
                          <Button
                            variant="destructive"
                            onClick={() => handleRevoke(key.keyId)}
                            disabled={revokeKey.isPending}
                          >
                            {revokeKey.isPending ? "Revoking..." : "Revoke"}
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
