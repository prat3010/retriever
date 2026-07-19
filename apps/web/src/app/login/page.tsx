"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setAdminKey = useAuthStore((s) => s.setKey);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) {
      setError("Master key is required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/v1/admin/tenants?limit=1`, {
        headers: { "X-Admin-Master-Key": key.trim() },
      });
      if (!res.ok) throw new Error("Invalid key");
    } catch {
      setLoading(false);
      setError("Invalid master key. Please try again.");
      return;
    }
    setAdminKey(key.trim());
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `admin_key=${encodeURIComponent(key.trim())}; path=/; max-age=86400; SameSite=Lax${secure}`;
    router.push("/");
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Retriever Admin</CardTitle>
          <CardDescription>Enter your admin master key to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="key">Admin Master Key</Label>
              <Input
                id="key"
                type="password"
                placeholder="Enter master key"
                value={key}
                onChange={(e) => { setKey(e.target.value); setError(""); }}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {loading ? "Verifying..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
