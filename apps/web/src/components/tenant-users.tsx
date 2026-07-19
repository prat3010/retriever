"use client";

import { useUsers, useCreateUser, useDeleteUser, type User } from "@/hooks/use-users";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Copy, Trash2 } from "lucide-react";
import { useState } from "react";

interface Props {
  tenantId: string;
}

export function UsersTab({ tenantId }: Props) {
  const { data: users, isLoading } = useUsers(tenantId);
  const createUser = useCreateUser(tenantId);
  const deleteUser = useDeleteUser(tenantId);
  const [open, setOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);
  const [externalId, setExternalId] = useState("");
  const [displayName, setDisplayName] = useState("");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!externalId.trim()) return;
    createUser.mutate(
      { external_id: externalId.trim(), display_name: displayName.trim() || undefined },
      {
        onSuccess: () => {
          toast.success("User created");
          setOpen(false);
          setExternalId("");
          setDisplayName("");
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Users</h3>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>Add User</Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleCreate}>
              <DialogHeader>
                <DialogTitle>Create User</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="externalId">External ID *</Label>
                  <Input
                    id="externalId"
                    value={externalId}
                    onChange={(e) => setExternalId(e.target.value)}
                    placeholder="user@example.com"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="displayName">Display Name</Label>
                  <Input
                    id="displayName"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Alice"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={createUser.isPending}>
                  {createUser.isPending ? "Creating..." : "Create"}
                </Button>
              </DialogFooter>
            </form>
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
              <TableHead>User ID</TableHead>
              <TableHead>External ID</TableHead>
              <TableHead>Display Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-12" />
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {users?.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  No users found
                </TableCell>
              </TableRow>
            )}
            {users?.map((user) => (
              <TableRow key={user.userId}>
                <TableCell className="font-mono text-xs">
                  <span className="flex items-center gap-1">
                    {user.userId.slice(0, 12)}…
                    <button
                      className="inline-flex items-center justify-center rounded p-0.5 opacity-40 hover:opacity-100 transition-opacity"
                      onClick={() => { navigator.clipboard.writeText(user.userId); toast.success("User ID copied"); }}
                      title="Copy User ID"
                    >
                      <Copy className="h-3 w-3" />
                    </button>
                  </span>
                </TableCell>
                <TableCell className="font-medium">{user.externalId}</TableCell>
                <TableCell className="text-muted-foreground">
                  {user.displayName ?? "—"}
                </TableCell>
                <TableCell>
                  <Badge variant={user.isActive ? "default" : "secondary"}>
                    {user.isActive ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(user.createdAt).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <button
                    className="inline-flex items-center justify-center rounded p-1 opacity-40 hover:opacity-100 hover:text-red-500 transition-opacity"
                    onClick={() => setDeleteTarget(user)}
                    title="Delete user"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Permanently deactivate user{" "}
            <span className="font-mono font-medium text-foreground">
              {deleteTarget?.externalId}
            </span>
            ?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleteUser.isPending}
              onClick={() => {
                if (!deleteTarget) return;
                deleteUser.mutate(deleteTarget.userId, {
                  onSuccess: () => {
                    toast.success("User deactivated");
                    setDeleteTarget(null);
                  },
                  onError: (err) => toast.error(err.message),
                });
              }}
            >
              {deleteUser.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
