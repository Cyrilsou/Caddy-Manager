import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { listCertificates, refreshCertificates } from "@/api/certificates";
import { formatDate, daysUntil } from "@/lib/utils";

interface Cert {
  id: number; hostname: string; issuer: string | null;
  not_before: string | null; not_after: string | null;
  status: string; last_checked_at: string | null;
  error_message: string | null;
}

export default function CertificatesPage() {
  const queryClient = useQueryClient();

  const { data: certs = [] } = useQuery({
    queryKey: ["certificates"],
    queryFn: () => listCertificates().then((r) => r.data),
  });

  const refreshMut = useMutation({
    mutationFn: () => refreshCertificates(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["certificates"] }),
  });

  const statusBadge = (status: string) => {
    switch (status) {
      case "valid": return <Badge variant="success">Valid</Badge>;
      case "expiring_soon": return <Badge variant="warning">Expiring Soon</Badge>;
      case "expired": return <Badge variant="danger">Expired</Badge>;
      case "error": return <Badge variant="danger">Error</Badge>;
      default: return <Badge variant="secondary">Pending</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Certificates</h1>
        <Button variant="outline" onClick={() => refreshMut.mutate()} disabled={refreshMut.isPending}>
          <RefreshCw className="mr-2 h-4 w-4" />Refresh All
        </Button>
      </div>

      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">Domain</th>
              <th className="p-3 text-left font-medium">Issuer</th>
              <th className="p-3 text-left font-medium">Expires</th>
              <th className="p-3 text-left font-medium">Days Left</th>
              <th className="p-3 text-left font-medium">Status</th>
              <th className="p-3 text-left font-medium">Last Check</th>
            </tr>
          </thead>
          <tbody>
            {certs.map((c: Cert) => {
              const days = daysUntil(c.not_after);
              return (
                <tr key={c.id} className="border-b">
                  <td className="p-3 font-mono text-sm">{c.hostname}</td>
                  <td className="p-3 text-muted-foreground">{c.issuer || "—"}</td>
                  <td className="p-3 text-muted-foreground">{formatDate(c.not_after)}</td>
                  <td className="p-3">
                    {days !== null ? (
                      <span className={days < 7 ? "text-red-400" : days < 30 ? "text-amber-400" : "text-emerald-400"}>
                        {days}d
                      </span>
                    ) : "—"}
                  </td>
                  <td className="p-3">{statusBadge(c.status)}</td>
                  <td className="p-3 text-xs text-muted-foreground">{formatDate(c.last_checked_at)}</td>
                </tr>
              );
            })}
            {certs.length === 0 && (
              <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No certificates tracked yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
