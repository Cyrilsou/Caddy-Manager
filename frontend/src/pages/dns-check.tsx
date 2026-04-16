import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, CheckCircle, XCircle, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { verifyDns, verifyAllDomains } from "@/api/dns";

interface DnsResult { hostname: string; status: string; message: string; resolved_ips: string[]; match: boolean; }

export default function DnsCheckPage() {
  const [hostname, setHostname] = useState("");
  const [expectedIp, setExpectedIp] = useState("");

  const singleMut = useMutation({
    mutationFn: () => verifyDns(hostname, expectedIp).then((r) => r.data),
  });

  const bulkMut = useMutation({
    mutationFn: () => verifyAllDomains(expectedIp).then((r) => r.data as DnsResult[]),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">DNS Verification</h1>

      <Card>
        <CardHeader>
          <CardTitle>Check Single Domain</CardTitle>
          <CardDescription>Verify that a hostname resolves to your proxy VM IP</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Hostname</Label>
              <Input value={hostname} onChange={(e) => setHostname(e.target.value)} placeholder="app.example.com" />
            </div>
            <div className="space-y-2">
              <Label>Expected IP (your VM)</Label>
              <Input value={expectedIp} onChange={(e) => setExpectedIp(e.target.value)} placeholder="203.0.113.10" />
            </div>
          </div>
          <Button onClick={() => singleMut.mutate()} disabled={!hostname || !expectedIp || singleMut.isPending}>
            <Search className="mr-2 h-4 w-4" />{singleMut.isPending ? "Checking..." : "Check DNS"}
          </Button>
          {singleMut.data && (
            <div className="flex items-center gap-3 rounded-lg border p-3">
              {singleMut.data.match ? <CheckCircle className="h-5 w-5 text-emerald-400" /> : <XCircle className="h-5 w-5 text-red-400" />}
              <div>
                <p className="font-mono text-sm">{singleMut.data.hostname}</p>
                <p className="text-xs text-muted-foreground">{singleMut.data.message}</p>
                <p className="text-xs text-muted-foreground">Resolved: {singleMut.data.resolved_ips.join(", ") || "none"}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Verify All Active Domains</CardTitle>
          <CardDescription>Check DNS for every active domain in the panel</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4 items-end">
            <div className="space-y-2">
              <Label>Your VM Public IP</Label>
              <Input value={expectedIp} onChange={(e) => setExpectedIp(e.target.value)} placeholder="203.0.113.10" className="w-64" />
            </div>
            <Button onClick={() => bulkMut.mutate()} disabled={!expectedIp || bulkMut.isPending}>
              <Globe className="mr-2 h-4 w-4" />{bulkMut.isPending ? "Checking all..." : "Check All Domains"}
            </Button>
          </div>
          {bulkMut.data && (
            <div className="space-y-2">
              {bulkMut.data.map((r: DnsResult) => (
                <div key={r.hostname} className="flex items-center justify-between rounded-lg border p-2">
                  <div className="flex items-center gap-2">
                    {r.match ? <CheckCircle className="h-4 w-4 text-emerald-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                    <span className="font-mono text-sm">{r.hostname}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{r.resolved_ips.join(", ")}</span>
                    <Badge variant={r.match ? "success" : "danger"}>{r.status}</Badge>
                  </div>
                </div>
              ))}
              <p className="text-sm text-muted-foreground">
                {bulkMut.data.filter((r: DnsResult) => r.match).length}/{bulkMut.data.length} domains OK
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
