import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, Shield, UserCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { listUsers, createUser, updateUser, deleteUser } from "@/api/users";

interface UserItem {
  id: number; username: string; email: string | null; role: string;
  is_active: boolean; is_superadmin: boolean; totp_enabled: boolean;
  last_login_at: string | null;
}

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ username: "", password: "", email: "", role: "viewer", is_active: true });

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => listUsers().then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => createUser(data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["users"] }); setDialogOpen(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => updateUser(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["users"] }); setDialogOpen(false); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const openCreate = () => {
    setEditingId(null);
    setForm({ username: "", password: "", email: "", role: "viewer", is_active: true });
    setDialogOpen(true);
  };

  const openEdit = (u: UserItem) => {
    setEditingId(u.id);
    setForm({ username: u.username, password: "", email: u.email || "", role: u.role, is_active: u.is_active });
    setDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingId) {
      updateMut.mutate({ id: editingId, data: { email: form.email || null, role: form.role, is_active: form.is_active } });
    } else {
      createMut.mutate(form);
    }
  };

  const roleBadge = (role: string, superadmin: boolean) => {
    if (superadmin) return <Badge variant="default">Superadmin</Badge>;
    switch (role) {
      case "admin": return <Badge variant="success">Admin</Badge>;
      case "editor": return <Badge variant="warning">Editor</Badge>;
      default: return <Badge variant="secondary">Viewer</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Users</h1>
        <Button onClick={openCreate}><Plus className="mr-2 h-4 w-4" />Add User</Button>
      </div>

      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="p-3 text-left font-medium">Username</th>
              <th className="p-3 text-left font-medium">Role</th>
              <th className="p-3 text-left font-medium">Status</th>
              <th className="p-3 text-left font-medium">2FA</th>
              <th className="p-3 text-left font-medium">Last Login</th>
              <th className="p-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u: UserItem) => (
              <tr key={u.id} className="border-b">
                <td className="p-3 flex items-center gap-2">
                  <UserCircle className="h-4 w-4 text-muted-foreground" />
                  {u.username}
                </td>
                <td className="p-3">{roleBadge(u.role, u.is_superadmin)}</td>
                <td className="p-3">
                  <Badge variant={u.is_active ? "success" : "danger"}>{u.is_active ? "Active" : "Disabled"}</Badge>
                </td>
                <td className="p-3">
                  {u.totp_enabled ? <Shield className="h-4 w-4 text-emerald-400" /> : <span className="text-muted-foreground">—</span>}
                </td>
                <td className="p-3 text-xs text-muted-foreground">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}</td>
                <td className="p-3 text-right">
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => openEdit(u)} disabled={u.is_superadmin}><Pencil className="h-3 w-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => { if (confirm(`Delete ${u.username}?`)) deleteMut.mutate(u.id); }} disabled={u.is_superadmin}><Trash2 className="h-3 w-3" /></Button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No users</td></tr>}
          </tbody>
        </table>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit User" : "Create User"}</DialogTitle>
            <DialogDescription>{editingId ? "Update role and status." : "Create a new user account."}</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!editingId && (
              <>
                <div className="space-y-2">
                  <Label>Username</Label>
                  <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required minLength={3} />
                </div>
                <div className="space-y-2">
                  <Label>Password</Label>
                  <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
                </div>
              </>
            )}
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="editor">Editor</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {editingId && (
              <div className="flex items-center gap-2">
                <Switch checked={form.is_active} onCheckedChange={(v) => setForm({ ...form, is_active: v })} />
                <Label>Active</Label>
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
