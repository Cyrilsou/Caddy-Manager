import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { listAuditLogs } from "@/api/audit";
import { formatDate } from "@/lib/utils";

interface AuditEntry {
  id: number; action: string; resource_type: string | null;
  resource_id: number | null; details: Record<string, unknown> | null;
  ip_address: string | null; user_agent: string | null;
  created_at: string;
}

const ACTIONS = [
  "auth.login", "auth.login_failed", "auth.password_change",
  "domain.create", "domain.update", "domain.delete", "domain.toggle",
  "backend.create", "backend.update", "backend.delete",
  "config.apply", "config.rollback", "setting.update",
];

export default function AuditLogPage() {
  const [action, setAction] = useState<string>("");
  const [page, setPage] = useState(1);

  const { data } = useQuery({
    queryKey: ["audit", action, page],
    queryFn: () => listAuditLogs({
      action: action || undefined,
      page,
      per_page: 50,
    }).then((r) => r.data),
  });

  const items: AuditEntry[] = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 50);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Audit Log</h1>

      <div className="flex gap-4">
        <Select value={action} onValueChange={(v) => { setAction(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-64"><SelectValue placeholder="Filter by action" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {ACTIONS.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground self-center">{total} entries</span>
      </div>

      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">Time</th>
              <th className="p-3 text-left font-medium">Action</th>
              <th className="p-3 text-left font-medium">Resource</th>
              <th className="p-3 text-left font-medium">IP</th>
              <th className="p-3 text-left font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {items.map((entry) => (
              <tr key={entry.id} className="border-b">
                <td className="p-3 text-xs text-muted-foreground whitespace-nowrap">{formatDate(entry.created_at)}</td>
                <td className="p-3"><Badge variant="secondary">{entry.action}</Badge></td>
                <td className="p-3 text-muted-foreground">
                  {entry.resource_type ? `${entry.resource_type}#${entry.resource_id}` : "—"}
                </td>
                <td className="p-3 font-mono text-xs text-muted-foreground">{entry.ip_address || "—"}</td>
                <td className="p-3 text-xs text-muted-foreground max-w-xs truncate">
                  {entry.details ? JSON.stringify(entry.details) : "—"}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No audit logs found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="self-center text-sm text-muted-foreground">Page {page} of {totalPages}</span>
          <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </div>
  );
}
