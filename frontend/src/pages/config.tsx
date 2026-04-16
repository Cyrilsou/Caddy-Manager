import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, RotateCcw, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { previewConfig, applyConfig, listVersions, rollbackVersion, getCaddyStatus } from "@/api/config";
import { formatDate } from "@/lib/utils";

interface Version {
  id: number; version_number: number; config_hash: string;
  is_active: boolean; applied_at: string | null;
  rollback_of_id: number | null; change_summary: string | null;
  created_at: string;
}

export default function ConfigPage() {
  const queryClient = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<{ config_json: object; has_changes: boolean } | null>(null);

  const { data: caddyStatus } = useQuery({
    queryKey: ["caddy-status"],
    queryFn: () => getCaddyStatus().then((r) => r.data),
    refetchInterval: 15_000,
  });

  const { data: versions = [] } = useQuery({
    queryKey: ["config-versions"],
    queryFn: () => listVersions().then((r) => r.data),
  });

  const previewMut = useMutation({
    mutationFn: () => previewConfig().then((r) => r.data),
    onSuccess: (data) => { setPreviewData(data); setPreviewOpen(true); },
  });

  const applyMut = useMutation({
    mutationFn: () => applyConfig().then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config-versions"] });
      queryClient.invalidateQueries({ queryKey: ["caddy-status"] });
    },
  });

  const rollbackMut = useMutation({
    mutationFn: (id: number) => rollbackVersion(id).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config-versions"] });
      queryClient.invalidateQueries({ queryKey: ["caddy-status"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Configuration</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => previewMut.mutate()} disabled={previewMut.isPending}>
            <Eye className="mr-2 h-4 w-4" />Preview
          </Button>
          <Button onClick={() => { if (confirm("Apply configuration to Caddy?")) applyMut.mutate(); }} disabled={applyMut.isPending}>
            <Play className="mr-2 h-4 w-4" />Apply to Caddy
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Caddy Status
            <Badge variant={caddyStatus?.reachable ? "success" : "danger"}>
              {caddyStatus?.reachable ? "Running" : "Unreachable"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{caddyStatus?.message}</p>
          {applyMut.isSuccess && (
            <p className="text-sm text-emerald-400 mt-2">Configuration applied successfully!</p>
          )}
          {applyMut.isError && (
            <p className="text-sm text-red-400 mt-2">Failed to apply: {(applyMut.error as Error).message}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Version History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {versions.map((v: Version) => (
              <div key={v.id} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold">v{v.version_number}</span>
                    {v.is_active && <Badge variant="success">Active</Badge>}
                    {v.rollback_of_id && <Badge variant="warning">Rollback</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {v.change_summary || "No description"} — {formatDate(v.applied_at || v.created_at)}
                  </p>
                </div>
                {!v.is_active && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { if (confirm(`Rollback to v${v.version_number}?`)) rollbackMut.mutate(v.id); }}
                    disabled={rollbackMut.isPending}
                  >
                    <RotateCcw className="mr-1 h-3 w-3" />Rollback
                  </Button>
                )}
              </div>
            ))}
            {versions.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">No configuration versions yet. Click "Apply to Caddy" to create the first one.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Configuration Preview</DialogTitle>
            <DialogDescription>
              {previewData?.has_changes ? "Changes detected from current active config." : "No changes from current active config."}
            </DialogDescription>
          </DialogHeader>
          <pre className="rounded-lg bg-muted p-4 text-xs overflow-x-auto">
            {JSON.stringify(previewData?.config_json, null, 2)}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
