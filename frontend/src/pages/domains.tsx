import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, Power } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { TableSkeleton } from "@/components/shared/loading-spinner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { listDomains, createDomain, updateDomain, deleteDomain, toggleDomain } from "@/api/domains";
import { listBackends } from "@/api/backends";
import { useDebounce } from "@/hooks/use-debounce";

interface DomainItem {
  id: number; hostname: string; backend_id: number; backend_name: string;
  backend_address: string; is_active: boolean; force_https: boolean;
  enable_websocket: boolean; maintenance_mode: boolean; cert_status: string | null;
  path_prefix: string; strip_prefix: boolean;
}

interface BackendItem { id: number; name: string; }

const defaultForm = {
  hostname: "", backend_id: "", is_active: true, force_https: true,
  enable_websocket: false, maintenance_mode: false, path_prefix: "/",
  strip_prefix: false, notes: "",
};

export default function DomainsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  const { data: domains = [], isLoading } = useQuery({
    queryKey: ["domains", debouncedSearch],
    queryFn: () => listDomains({ search: debouncedSearch || undefined }).then((r) => r.data),
  });

  const { data: backends = [] } = useQuery({
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
    mutationFn: (data: Record<string, unknown>) => createDomain(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["domains"] }); setDialogOpen(false); setError(""); },
    onError: onMutError,
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => updateDomain(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["domains"] }); setDialogOpen(false); setError(""); },
    onError: onMutError,
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteDomain(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["domains"] }),
    onError: onMutError,
  });

  const toggleMut = useMutation({
    mutationFn: (id: number) => toggleDomain(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["domains"] }),
    onError: onMutError,
  });

  const openCreate = () => {
    setEditingId(null);
    setForm(defaultForm);
    setDialogOpen(true);
  };

  const openEdit = (d: DomainItem) => {
    setEditingId(d.id);
    setForm({
      hostname: d.hostname, backend_id: String(d.backend_id), is_active: d.is_active,
      force_https: d.force_https, enable_websocket: d.enable_websocket,
      maintenance_mode: d.maintenance_mode, path_prefix: d.path_prefix,
      strip_prefix: d.strip_prefix, notes: "",
    });
    setDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = { ...form, backend_id: parseInt(form.backend_id) };
    if (editingId) {
      updateMut.mutate({ id: editingId, data });
    } else {
      createMut.mutate(data);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Domains</h1>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Add Domain</Button>
      </div>

      <Input placeholder="Search domains..." value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {isLoading ? <TableSkeleton rows={5} cols={5} /> : (
      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">Hostname</th>
              <th className="p-3 text-left font-medium">Backend</th>
              <th className="p-3 text-left font-medium">Status</th>
              <th className="p-3 text-left font-medium">TLS</th>
              <th className="p-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {domains.map((d: DomainItem) => (
              <tr key={d.id} className="border-b">
                <td className="p-3 font-mono text-sm">{d.hostname}</td>
                <td className="p-3">
                  <span className="text-muted-foreground">{d.backend_name}</span>
                  <span className="text-xs text-muted-foreground ml-1">({d.backend_address})</span>
                </td>
                <td className="p-3">
                  {d.maintenance_mode ? (
                    <Badge variant="warning">Maintenance</Badge>
                  ) : d.is_active ? (
                    <Badge variant="success">Active</Badge>
                  ) : (
                    <Badge variant="secondary">Inactive</Badge>
                  )}
                </td>
                <td className="p-3">
                  {d.cert_status === "valid" && <Badge variant="success">Valid</Badge>}
                  {d.cert_status === "expiring_soon" && <Badge variant="warning">Expiring</Badge>}
                  {d.cert_status === "expired" && <Badge variant="danger">Expired</Badge>}
                  {!d.cert_status && <Badge variant="secondary">Pending</Badge>}
                </td>
                <td className="p-3 text-right">
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => toggleMut.mutate(d.id)}>
                      <Power className="h-3 w-3" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => openEdit(d)}>
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => { if (confirm(`Delete ${d.hostname}?`)) deleteMut.mutate(d.id); }}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {domains.length === 0 && (
              <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No domains configured</td></tr>
            )}
          </tbody>
        </table>
      </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Domain" : "Add Domain"}</DialogTitle>
            <DialogDescription>Configure the domain routing.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Hostname</Label>
              <Input value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} required placeholder="app.example.com" />
            </div>
            <div className="space-y-2">
              <Label>Backend</Label>
              <Select value={form.backend_id} onValueChange={(v) => setForm({ ...form, backend_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select backend" /></SelectTrigger>
                <SelectContent>
                  {backends.map((b: BackendItem) => (
                    <SelectItem key={b.id} value={String(b.id)}>{b.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Path Prefix</Label>
                <Input value={form.path_prefix} onChange={(e) => setForm({ ...form, path_prefix: e.target.value })} />
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Switch checked={form.force_https} onCheckedChange={(v) => setForm({ ...form, force_https: v })} />
                <Label>Force HTTPS</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.enable_websocket} onCheckedChange={(v) => setForm({ ...form, enable_websocket: v })} />
                <Label>WebSocket Support</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.strip_prefix} onCheckedChange={(v) => setForm({ ...form, strip_prefix: v })} />
                <Label>Strip Path Prefix</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.maintenance_mode} onCheckedChange={(v) => setForm({ ...form, maintenance_mode: v })} />
                <Label>Maintenance Mode</Label>
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={createMut.isPending || updateMut.isPending}>
              {editingId ? "Update" : "Create"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
