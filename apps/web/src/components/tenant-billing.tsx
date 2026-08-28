"use client";

import { useState } from "react";
import { useCreateCheckoutSession, usePaymentLedger } from "@/hooks/use-billing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

interface TenantBillingTabProps {
  tenantId: string;
}

export function TenantBillingTab({ tenantId }: TenantBillingTabProps) {
  const { data, isLoading } = usePaymentLedger(tenantId);
  const checkoutMutation = useCreateCheckoutSession();

  const [planId, setPlanId] = useState("pro_inr");
  const [amount, setAmount] = useState(2499);
  const [currency, setCurrency] = useState("INR");
  const [provider, setProvider] = useState("stripe");
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);

  const handleCreateCheckout = () => {
    checkoutMutation.mutate(
      {
        tenant_id: tenantId,
        plan_id: planId,
        provider,
        amount,
        currency,
      },
      {
        onSuccess: (res) => {
          setGeneratedUrl(res.checkout_url);
        },
      }
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Checkout Generator Card */}
      <Card>
        <CardHeader>
          <CardTitle>Manual Commercial Deposit & Checkout Generator</CardTitle>
          <CardDescription>Issue cryptographic payment checkout links for Stripe, Razorpay, or PhonePe.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="billing-plan-tier">Plan Tier</Label>
              <Select value={planId} onValueChange={setPlanId}>
                <SelectTrigger id="billing-plan-tier">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="starter_inr">Starter Tier</SelectItem>
                  <SelectItem value="pro_inr">Pro Tier ($2,499)</SelectItem>
                  <SelectItem value="business_inr">Business Tier ($5,999)</SelectItem>
                  <SelectItem value="enterprise">Enterprise Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="billing-gateway">Gateway Provider</Label>
              <Select value={provider} onValueChange={setProvider}>
                <SelectTrigger id="billing-gateway">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="stripe">Stripe</SelectItem>
                  <SelectItem value="razorpay">Razorpay</SelectItem>
                  <SelectItem value="phonepe">PhonePe</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="billing-amount">Amount</Label>
              <Input
                id="billing-amount"
                type="number"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="billing-currency">Currency</Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger id="billing-currency">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INR">INR (₹)</SelectItem>
                  <SelectItem value="USD">USD ($)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={handleCreateCheckout} disabled={checkoutMutation.isPending} aria-label="Generate checkout link">
            {checkoutMutation.isPending ? "Generating..." : "Generate Checkout Link"}
          </Button>

          {generatedUrl && (
            <div className="p-3 bg-muted rounded font-mono text-xs flex items-center justify-between">
              <span className="truncate mr-2">{generatedUrl}</span>
              <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(generatedUrl)} aria-label="Copy generated checkout link">
                Copy Link
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Transaction History Ledger */}
      <Card>
        <CardHeader>
          <CardTitle>Commercial Payment Ledger</CardTitle>
          <CardDescription>Audit-proof transaction ledger with cryptographic webhook verification.</CardDescription>
        </CardHeader>
        <CardContent>
          {!data?.transactions || data.transactions.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No payment transactions recorded for this tenant.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Event Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.transactions.map((tx) => (
                  <TableRow key={tx.transaction_id}>
                    <TableCell className="font-mono text-xs">{new Date(tx.created_at).toLocaleString()}</TableCell>
                    <TableCell className="font-mono text-xs">{tx.transaction_id.slice(0, 8)}...</TableCell>
                    <TableCell className="capitalize font-medium">{tx.provider}</TableCell>
                    <TableCell className="font-mono text-xs">{tx.event_type}</TableCell>
                    <TableCell className="font-mono font-bold">
                      {tx.currency === "INR" ? "₹" : "$"}{tx.amount}
                    </TableCell>
                    <TableCell>
                      <Badge variant={tx.status === "completed" ? "outline" : "secondary"}>
                        {tx.status}
                      </Badge>
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
