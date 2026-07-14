"use client";

import { Tenant, useDeactivateTenant } from "@/hooks/use-tenants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useState } from "react";

interface Props {
  tenant: Tenant;
  tenantId: string;
}

export function OverviewTab({ tenant, tenantId }: Props) {
  const deactivate = useDeactivateTenant();
  const [open, setOpen] = useState(false);

  function handleDeactivate() {
    deactivate.mutate(tenantId, {
      onSuccess: () => {
        toast.success("Tenant deactivated");
        setOpen(false);
      },
      onError: () => toast.error("Failed to deactivate tenant"),
    });
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Tenant Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Name</span>
            <span className="font-medium">{tenant.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <Badge variant={tenant.status === "active" ? "default" : "secondary"}>
              {tenant.status}
            </Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Tier</span>
            <span>{tenant.tier}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Created</span>
            <span>{new Date(tenant.createdAt).toLocaleDateString()}</span>
          </div>
        </CardContent>
      </Card>

      {tenant.status === "active" && (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive">Deactivate Tenant</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Deactivate tenant?</DialogTitle>
              <DialogDescription>
                This will suspend &quot;{tenant.name}&quot;. All users will be blocked
                from accessing the platform.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeactivate}
                disabled={deactivate.isPending}
              >
                {deactivate.isPending ? "Deactivating..." : "Deactivate"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
