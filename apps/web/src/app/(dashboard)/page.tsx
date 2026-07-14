"use client";

import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Topbar } from "@/components/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTenants } from "@/hooks/use-tenants";
import { Building2, Users, Key, FileText } from "lucide-react";

export default function DashboardPage() {
  const adminKey = useAuthStore((s) => s.adminKey);
  const router = useRouter();
  const { data: tenants, isLoading } = useTenants();

  useEffect(() => {
    if (!adminKey) router.push("/login");
  }, [adminKey, router]);

  if (!adminKey) return null;

  const stats = [
    {
      title: "Total Tenants",
      value: tenants?.total ?? 0,
      icon: Building2,
    },
    {
      title: "Active",
      value: tenants?.items?.filter((t) => t.status === "active").length ?? 0,
      icon: Users,
    },
    {
      title: "Suspended",
      value: tenants?.items?.filter((t) => t.status === "suspended").length ?? 0,
      icon: Key,
    },
    {
      title: "Tiers",
      value: new Set(tenants?.items?.map((t) => t.tier)).size ?? 0,
      icon: FileText,
    },
  ];

  return (
    <div>
      <Topbar title="Dashboard" description="Platform overview" />
      <div className="p-6 space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.title}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <Skeleton className="h-8 w-16" />
                  ) : (
                    <div className="text-2xl font-bold">{stat.value}</div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
