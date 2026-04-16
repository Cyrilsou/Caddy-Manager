import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Cloud, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { verifyToken, listZones, listDnsRecords, deleteDnsRecord, toggleProxy } from "@/api/cloudflare";

interface Zone { id: string; name: string; status: string; }
interface DnsRecord { id: string; type: string; name: string; content: string; proxied: boolean; ttl: number; }

export default function CloudflarePage() {
  const queryClient = useQueryClient();
  const [selectedZone, setSelectedZone] = useState<string>("");

  const { data: verification } = useQuery({
    queryKey: ["cf-verify"],
    queryFn: () => verifyToken().then((r) => r.data),
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["cf-zones"],
    queryFn: () => listZones().then((r) => r.data),
    enabled: verification?.valid === true,
  });

  const { data: records = [] } = useQuery({
    queryKey: ["cf-dns", selectedZone],
    queryFn: () => listDnsRecords(selectedZone).then((r) => r.data),
    enabled: !!selectedZone,
  });

  const deleteMut = useMutation({
    mutationFn: (recordId: string) => deleteDnsRecord(selectedZone, recordId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cf-dns", selectedZone] }),
  });

  const toggleMut = useMutation({
    mutationFn: ({ recordId, proxied }: { recordId: string; proxied: boolean }) =>
      toggleProxy({ zone_id: selectedZone, record_id: recordId, proxied }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cf-dns", selectedZone] }),
  });

  if (!verification) {
    return <div className="text-muted-foreground">Checking Cloudflare token...</div>;
  }

  if (!verification.valid) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Cloudflare</h1>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <Cloud className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Cloudflare API not configured</p>
                <p className="text-sm text-muted-foreground">
                  Set CLOUDFLARE_API_TOKEN in your .env file to enable DNS management.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Cloudflare DNS</h1>
        <Badge variant="success">API Connected</Badge>
      </div>

      <div className="max-w-sm">
        <Select value={selectedZone} onValueChange={setSelectedZone}>
          <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
          <SelectContent>
            {zones.map((z: Zone) => (
              <SelectItem key={z.id} value={z.id}>{z.name} ({z.status})</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedZone && (
        <div className="rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="p-3 text-left font-medium">Type</th>
                <th className="p-3 text-left font-medium">Name</th>
                <th className="p-3 text-left font-medium">Content</th>
                <th className="p-3 text-left font-medium">Proxy</th>
                <th className="p-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r: DnsRecord) => (
                <tr key={r.id} className="border-b">
                  <td className="p-3"><Badge variant="secondary">{r.type}</Badge></td>
                  <td className="p-3 font-mono text-xs">{r.name}</td>
                  <td className="p-3 font-mono text-xs text-muted-foreground">{r.content}</td>
                  <td className="p-3">
                    <Badge variant={r.proxied ? "warning" : "secondary"}>
                      {r.proxied ? "Proxied" : "DNS only"}
                    </Badge>
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => toggleMut.mutate({ recordId: r.id, proxied: !r.proxied })}
                      >
                        {r.proxied ? <ToggleRight className="h-3 w-3" /> : <ToggleLeft className="h-3 w-3" />}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => { if (confirm(`Delete ${r.name}?`)) deleteMut.mutate(r.id); }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No DNS records</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
