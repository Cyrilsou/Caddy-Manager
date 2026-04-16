import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { listSettings, updateSetting } from "@/api/settings";
import { changePassword } from "@/api/auth";

interface SettingItem { key: string; value: string; is_secret: boolean; }

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [passwordForm, setPasswordForm] = useState({ current: "", new: "", confirm: "" });
  const [passwordMsg, setPasswordMsg] = useState("");

  const { data: settings = [] } = useQuery({
    queryKey: ["settings"],
    queryFn: () => listSettings().then((r) => r.data),
  });

  const updateMut = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => updateSetting(key, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg("");
    if (passwordForm.new !== passwordForm.confirm) {
      setPasswordMsg("Passwords do not match");
      return;
    }
    try {
      await changePassword(passwordForm.current, passwordForm.new);
      setPasswordMsg("Password changed successfully");
      setPasswordForm({ current: "", new: "", confirm: "" });
    } catch {
      setPasswordMsg("Failed to change password");
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Application Settings</CardTitle>
          <CardDescription>Configure panel behavior</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settings.map((s: SettingItem) => (
            <div key={s.key} className="flex items-center gap-4">
              <Label className="w-48 text-right font-mono text-xs">{s.key}</Label>
              <Input
                type={s.is_secret ? "password" : "text"}
                defaultValue={s.value}
                className="flex-1"
                onBlur={(e) => {
                  if (e.target.value !== s.value) {
                    updateMut.mutate({ key: s.key, value: e.target.value });
                  }
                }}
              />
            </div>
          ))}
          {settings.length === 0 && (
            <p className="text-sm text-muted-foreground">No settings configured</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Update your admin password</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
            {passwordMsg && (
              <div className={`rounded-md p-3 text-sm ${passwordMsg.includes("success") ? "bg-emerald-500/10 text-emerald-400" : "bg-destructive/10 text-destructive"}`}>
                {passwordMsg}
              </div>
            )}
            <div className="space-y-2">
              <Label>Current Password</Label>
              <Input type="password" value={passwordForm.current} onChange={(e) => setPasswordForm({ ...passwordForm, current: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>New Password</Label>
              <Input type="password" value={passwordForm.new} onChange={(e) => setPasswordForm({ ...passwordForm, new: e.target.value })} required minLength={8} />
            </div>
            <div className="space-y-2">
              <Label>Confirm New Password</Label>
              <Input type="password" value={passwordForm.confirm} onChange={(e) => setPasswordForm({ ...passwordForm, confirm: e.target.value })} required />
            </div>
            <Button type="submit">Change Password</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
