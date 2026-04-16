import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Trash2, BarChart3, Settings2, Gauge } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { listZones } from "@/api/cloudflare";
import {
  runSpeedTest, purgeAll, getCacheSettings, updateCacheSettings,
  autoOptimize, getCacheAnalytics,
} from "@/api/cache";

interface Zone { id: string; name: string; status: string; }

export default function CachePage() {
  const queryClient = useQueryClient();
  const [selectedZone, setSelectedZone] = useState("");
  const [purgeUrl, setPurgeUrl] = useState("");

  const { data: zones = [] } = useQuery({
    queryKey: ["cf-zones"],
    queryFn: () => listZones().then((r) => r.data),
  });

  const { data: cacheSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ["cache-settings", selectedZone],
    queryFn: () => getCacheSettings(selectedZone).then((r) => r.data),
    enabled: !!selectedZone,
  });

  const { data: analytics } = useQuery({
    queryKey: ["cache-analytics", selectedZone],
    queryFn: () => getCacheAnalytics(selectedZone).then((r) => r.data),
    enabled: !!selectedZone,
    refetchInterval: 60_000,
  });

  const speedTestMut = useMutation({
    mutationFn: () => runSpeedTest().then((r) => r.data),
  });

  const autoOptMut = useMutation({
    mutationFn: () => autoOptimize(selectedZone).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-settings", selectedZone] }),
  });

  const purgeMut = useMutation({
    mutationFn: () => purgeAll(selectedZone),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-analytics", selectedZone] }),
  });

  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateCacheSettings(selectedZone, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-settings", selectedZone] }),
  });

  const tierBadge = (tier: string) => {
    switch (tier) {
      case "aggressive": return <Badge variant="success">Aggressive CDN</Badge>;
      case "balanced": return <Badge variant="warning">Balanced</Badge>;
      case "light": return <Badge variant="secondary">Light</Badge>;
      default: return <Badge variant="secondary">{tier}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Cache CDN</h1>
      </div>

      {/* Zone selector */}
      <div className="max-w-sm">
        <Select value={selectedZone} onValueChange={setSelectedZone}>
          <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
          <SelectContent>
            {zones.map((z: Zone) => (
              <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Speed Test */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5" /> Speed Test</CardTitle>
          <CardDescription>Measure server bandwidth to determine optimal cache settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={() => speedTestMut.mutate()} disabled={speedTestMut.isPending}>
            <Zap className="mr-2 h-4 w-4" />
            {speedTestMut.isPending ? "Testing..." : "Run Speed Test"}
          </Button>

          {speedTestMut.data && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.download_mbps}</div>
                  <div className="text-xs text-muted-foreground">Download (Mbps)</div>
                </div>
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.upload_mbps}</div>
                  <div className="text-xs text-muted-foreground">Upload (Mbps)</div>
                </div>
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.latency_ms}</div>
                  <div className="text-xs text-muted-foreground">Latency (ms)</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">Recommendation:</span>
                {tierBadge(speedTestMut.data.recommendations.tier)}
                <span className="text-sm text-muted-foreground">{speedTestMut.data.recommendations.reason}</span>
              </div>
              {selectedZone && (
                <Button
                  onClick={() => autoOptMut.mutate()}
                  disabled={autoOptMut.isPending}
                  variant="default"
                >
                  <Settings2 className="mr-2 h-4 w-4" />
                  {autoOptMut.isPending ? "Applying..." : "Auto-Apply Recommended Settings"}
                </Button>
              )}
              {autoOptMut.isSuccess && (
                <p className="text-sm text-emerald-400">Settings applied: {autoOptMut.data.applied.tier} tier</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedZone && (
        <>
          {/* Analytics */}
          {analytics && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5" /> Cache Analytics (24h)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <div className="text-xl font-bold text-emerald-400">{analytics.request_hit_ratio}%</div>
                    <div className="text-xs text-muted-foreground">Request Hit Ratio</div>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <div className="text-xl font-bold text-emerald-400">{analytics.bandwidth_hit_ratio}%</div>
                    <div className="text-xs text-muted-foreground">Bandwidth Hit Ratio</div>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <div className="text-xl font-bold">{analytics.cached_bandwidth_mb}</div>
                    <div className="text-xs text-muted-foreground">Cached (MB)</div>
                  </div>
                  <div className="rounded-lg bg-muted p-3 text-center">
                    <div className="text-xl font-bold">{analytics.total_requests.toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Total Requests</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Cache Settings */}
          {settingsLoading ? <LoadingSpinner text="Loading cache settings..." /> : cacheSettings && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Settings2 className="h-5 w-5" /> Cache Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Cache Level</Label>
                    <Select
                      value={cacheSettings.cache_level}
                      onValueChange={(v) => updateMut.mutate({ cache_level: v })}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="aggressive">Aggressive</SelectItem>
                        <SelectItem value="basic">Basic</SelectItem>
                        <SelectItem value="simplified">Simplified</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Browser Cache TTL</Label>
                    <Select
                      value={String(cacheSettings.browser_cache_ttl)}
                      onValueChange={(v) => updateMut.mutate({ browser_cache_ttl: parseInt(v) })}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Respect Origin</SelectItem>
                        <SelectItem value="1800">30 min</SelectItem>
                        <SelectItem value="3600">1 hour</SelectItem>
                        <SelectItem value="7200">2 hours</SelectItem>
                        <SelectItem value="14400">4 hours</SelectItem>
                        <SelectItem value="86400">1 day</SelectItem>
                        <SelectItem value="604800">1 week</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Image Optimization (Polish)</Label>
                    <Select
                      value={cacheSettings.polish}
                      onValueChange={(v) => updateMut.mutate({ polish: v })}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="lossless">Lossless</SelectItem>
                        <SelectItem value="lossy">Lossy</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={cacheSettings.always_online === "on"}
                      onCheckedChange={(v) => updateMut.mutate({ always_online: v })}
                    />
                    <Label>Always Online</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={cacheSettings.rocket_loader === "on"}
                      onCheckedChange={(v) => updateMut.mutate({ rocket_loader: v })}
                    />
                    <Label>Rocket Loader (JS optimization)</Label>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Purge */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Trash2 className="h-5 w-5" /> Purge Cache</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="destructive"
                onClick={() => { if (confirm("Purge ALL cached content?")) purgeMut.mutate(); }}
                disabled={purgeMut.isPending}
              >
                {purgeMut.isPending ? "Purging..." : "Purge Everything"}
              </Button>
              {purgeMut.isSuccess && <p className="text-sm text-emerald-400">Cache purged successfully</p>}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
