import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe, Server, Shield, Activity, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getDashboardStats } from "@/api/dashboard";
import { listAuditLogs } from "@/api/audit";
import { formatDate } from "@/lib/utils";

interface ServerEvent {
  type: string;
  name?: string;
  status?: string;
  old_status?: string;
  [key: string]: unknown;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [alerts, setAlerts] = useState<ServerEvent[]>([]);

  // SSE for real-time events
  useEffect(() => {
    const es = new EventSource("/api/v1/events/stream", { withCredentials: true });
    es.onmessage = (event) => {
      try {
        const data: ServerEvent = JSON.parse(event.data);
        if (data.type === "backend_status") {
          setAlerts((prev) => [data, ...prev].slice(0, 10));
          queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
        }
      } catch { /* ignore */ }
    };
    return () => es.close();
  }, [queryClient]);
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => getDashboardStats().then((r) => r.data),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,  // Don't refetch when tab is hidden
  });

  const { data: auditData } = useQuery({
    queryKey: ["recent-audit"],
    queryFn: () => listAuditLogs({ per_page: 10 }).then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>

      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((a, i) => (
            <div key={i} className={`flex items-center gap-2 rounded-md p-3 text-sm ${
              a.status === "unhealthy" ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"
            }`}>
              <AlertTriangle className="h-4 w-4" />
              <span><strong>{a.name}</strong> is now <strong>{a.status}</strong> (was {a.old_status})</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Domains</CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_domains ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.total_domains ?? 0} total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Backends</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.healthy_backends ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.unhealthy_backends ?? 0} unhealthy, {stats?.unknown_backends ?? 0} unknown
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Certificates</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.certs_valid ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {(stats?.certs_expiring_soon ?? 0) > 0 && (
                <span className="text-amber-400">{stats?.certs_expiring_soon} expiring soon</span>
              )}
              {(stats?.certs_expired ?? 0) > 0 && (
                <span className="text-red-400"> {stats?.certs_expired} expired</span>
              )}
              {(stats?.certs_expiring_soon ?? 0) === 0 && (stats?.certs_expired ?? 0) === 0 && "All valid"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Caddy</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant={stats?.caddy_reachable ? "success" : "danger"}>
                {stats?.caddy_reachable ? "Running" : "Down"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Config v{stats?.config_version ?? "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {auditData?.items?.length === 0 && (
              <p className="text-sm text-muted-foreground">No recent activity</p>
            )}
            {auditData?.items?.map((log: { id: number; action: string; created_at: string; ip_address: string | null }) => (
              <div key={log.id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">{log.action}</Badge>
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatDate(log.created_at)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
