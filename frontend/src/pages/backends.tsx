import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { listBackends, createBackend, updateBackend, deleteBackend, checkBackendHealth } from "@/api/backends";
import { LoadingSpinner } from "@/components/shared/loading-spinner";

interface Backend {
  id: number;
  name: string;
  host: string;
  port: number;
  protocol: string;
  health_check_enabled: boolean;
  health_check_path: string;
  health_status: string;
  health_response_time_ms: number | null;
  domain_count: number;
}

export default function BackendsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: "", host: "", port: "80", protocol: "http", health_check_enabled: false, health_check_path: "/" });

  const { data: backends = [], isLoading } = useQuery({
    queryKey: ["backends"],
    queryFn: () => listBackends().then((r) => r.data),
  });

  const [error, setError] = useState("");

  const onMutError = (err: unknown) => {
    const axiosErr = err as { response?: { data?: { detail?: string } } };
    setError(axiosErr.response?.data?.detail || "An error occurred");
    setTimeout(() => setError(""), 5000);
  };

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => createBackend(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["backends"] }); setDialogOpen(false); setError(""); },
    onError: onMutError,
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => updateBackend(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["backends"] }); setDialogOpen(false); setError(""); },
    onError: onMutError,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteBackend(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backends"] }),
    onError: onMutError,
  });

  const healthMut = useMutation({
    mutationFn: (id: number) => checkBackendHealth(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backends"] }),
    onError: onMutError,
  });

  const openCreate = () => {
    setEditingId(null);
    setForm({ name: "", host: "", port: "80", protocol: "http", health_check_enabled: false, health_check_path: "/" });
    setDialogOpen(true);
  };

  const openEdit = (b: Backend) => {
    setEditingId(b.id);
    setForm({ name: b.name, host: b.host, port: String(b.port), protocol: b.protocol, health_check_enabled: b.health_check_enabled, health_check_path: b.health_check_path });
    setDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = { ...form, port: parseInt(form.port) };
    if (editingId) {
      updateMut.mutate({ id: editingId, data });
    } else {
      createMut.mutate(data);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case "healthy": return <Badge variant="success">Healthy</Badge>;
      case "unhealthy": return <Badge variant="danger">Unhealthy</Badge>;
      default: return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Backends</h1>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Add Backend</Button>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {isLoading ? <LoadingSpinner text="Loading backends..." /> : (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {backends.map((b: Backend) => (
          <Card key={b.id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base">{b.name}</CardTitle>
              {statusBadge(b.health_status)}
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{b.protocol}://{b.host}:{b.port}</p>
              <p className="text-xs text-muted-foreground mt-1">{b.domain_count} domain(s)</p>
              {b.health_response_time_ms !== null && (
                <p className="text-xs text-muted-foreground">{b.health_response_time_ms}ms</p>
              )}
              <div className="flex gap-2 mt-4">
                <Button size="sm" variant="outline" onClick={() => openEdit(b)}><Pencil className="h-3 w-3" /></Button>
                <Button size="sm" variant="outline" onClick={() => healthMut.mutate(b.id)}><Heart className="h-3 w-3" /></Button>
                <Button size="sm" variant="outline" onClick={() => { if (confirm("Delete this backend?")) deleteMut.mutate(b.id); }} disabled={b.domain_count > 0}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Backend" : "Add Backend"}</DialogTitle>
            <DialogDescription>Configure the backend server connection details.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Host / IP</Label>
                <Input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} required placeholder="192.168.1.10" />
              </div>
              <div className="space-y-2">
                <Label>Port</Label>
                <Input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} required min={1} max={65535} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Protocol</Label>
              <Select value={form.protocol} onValueChange={(v) => setForm({ ...form, protocol: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="http">HTTP</SelectItem>
                  <SelectItem value="https">HTTPS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={form.health_check_enabled} onCheckedChange={(v) => setForm({ ...form, health_check_enabled: v })} />
              <Label>Health Check</Label>
            </div>
            {form.health_check_enabled && (
              <div className="space-y-2">
                <Label>Health Check Path</Label>
                <Input value={form.health_check_path} onChange={(e) => setForm({ ...form, health_check_path: e.target.value })} />
              </div>
            )}
            <Button type="submit" className="w-full" disabled={createMut.isPending || updateMut.isPending}>
              {editingId ? "Update" : "Create"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
