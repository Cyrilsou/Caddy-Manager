import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Zap, Trash2, BarChart3, Settings2, Gauge, HardDrive, Cloud } from "lucide-react";
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
  runSpeedTest, getCacheStatus, purgeAll, getCacheSettings, updateCacheSettings,
  autoOptimize, getCacheAnalytics, getLocalCacheStats, localPurgeAll, localPurgeDomain,
} from "@/api/cache";

interface Zone { id: string; name: string; }

export default function CachePage() {
  const queryClient = useQueryClient();
  const [selectedZone, setSelectedZone] = useState("");
  const [purgeDomain, setPurgeDomain] = useState("");

  const { data: status } = useQuery({
    queryKey: ["cache-status"],
    queryFn: () => getCacheStatus().then((r) => r.data),
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["cf-zones"],
    queryFn: () => listZones().then((r) => r.data),
    enabled: status?.cloudflare_cdn === true,
  });

  const { data: cacheSettings } = useQuery({
    queryKey: ["cache-settings", selectedZone],
    queryFn: () => getCacheSettings(selectedZone).then((r) => r.data),
    enabled: !!selectedZone && status?.cloudflare_cdn,
  });

  const { data: analytics } = useQuery({
    queryKey: ["cache-analytics", selectedZone],
    queryFn: () => getCacheAnalytics(selectedZone).then((r) => r.data),
    enabled: !!selectedZone && status?.cloudflare_cdn,
  });

  const { data: localStats } = useQuery({
    queryKey: ["local-cache-stats"],
    queryFn: () => getLocalCacheStats().then((r) => r.data),
    enabled: status?.local_cdn === true || status?.local_cdn_available === true,
    refetchInterval: 30_000,
  });

  const speedTestMut = useMutation({ mutationFn: () => runSpeedTest().then((r) => r.data) });

  const autoOptMut = useMutation({
    mutationFn: () => autoOptimize(selectedZone).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-settings"] }),
  });

  const cfPurgeMut = useMutation({
    mutationFn: () => purgeAll(selectedZone),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-analytics"] }),
  });

  const localPurgeMut = useMutation({
    mutationFn: () => localPurgeAll(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["local-cache-stats"] }),
  });

  const localPurgeDomainMut = useMutation({
    mutationFn: (h: string) => localPurgeDomain(h),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["local-cache-stats"] }),
  });

  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateCacheSettings(selectedZone, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cache-settings"] }),
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
        {status && (
          <Badge variant={status.active === "none" ? "secondary" : "success"}>
            {status.active === "cloudflare" && <><Cloud className="h-3 w-3 mr-1" /> Cloudflare CDN</>}
            {status.active === "local" && <><HardDrive className="h-3 w-3 mr-1" /> Local CDN</>}
            {status.active === "none" && "No cache active"}
          </Badge>
        )}
      </div>

      {/* Speed Test — always available */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5" /> Speed Test</CardTitle>
          <CardDescription>Measure bandwidth to determine optimal cache strategy</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={() => speedTestMut.mutate()} disabled={speedTestMut.isPending}>
            <Zap className="mr-2 h-4 w-4" />{speedTestMut.isPending ? "Testing..." : "Run Speed Test"}
          </Button>
          {speedTestMut.data && (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.download_mbps}</div>
                  <div className="text-xs text-muted-foreground">Download Mbps</div>
                </div>
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.upload_mbps}</div>
                  <div className="text-xs text-muted-foreground">Upload Mbps</div>
                </div>
                <div className="rounded-lg bg-muted p-3 text-center">
                  <div className="text-2xl font-bold">{speedTestMut.data.speed_test.latency_ms}</div>
                  <div className="text-xs text-muted-foreground">Latency ms</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {tierBadge(speedTestMut.data.recommendations.tier)}
                <span className="text-sm text-muted-foreground">{speedTestMut.data.recommendations.reason}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ===== LOCAL CDN SECTION ===== */}
      {(status?.local_cdn || status?.local_cdn_available) && (
        <>
          <h2 className="text-xl font-semibold flex items-center gap-2"><HardDrive className="h-5 w-5" /> Local CDN (Souin)</h2>

          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Cached Entries</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-bold">{localStats?.total_entries ?? 0}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Domains Cached</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-bold">{Object.keys(localStats?.domains ?? {}).length}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Status</CardTitle></CardHeader>
              <CardContent>
                <Badge variant={localStats?.error ? "danger" : "success"}>
                  {localStats?.error ? "Error" : "Active"}
                </Badge>
              </CardContent>
            </Card>
          </div>

          {localStats?.domains && Object.keys(localStats.domains).length > 0 && (
            <Card>
              <CardHeader><CardTitle>Cache per Domain</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(localStats.domains as Record<string, number>).map(([domain, count]) => (
                    <div key={domain} className="flex items-center justify-between rounded-lg border p-2">
                      <div>
                        <span className="font-mono text-sm">{domain}</span>
                        <span className="text-xs text-muted-foreground ml-2">{count} entries</span>
                      </div>
                      <Button
                        size="sm" variant="outline"
                        onClick={() => localPurgeDomainMut.mutate(domain)}
                        disabled={localPurgeDomainMut.isPending}
                      >
                        <Trash2 className="h-3 w-3 mr-1" />Purge
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><CardTitle>Purge Local Cache</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input value={purgeDomain} onChange={(e) => setPurgeDomain(e.target.value)} placeholder="app.example.com" className="max-w-sm" />
                <Button variant="outline" onClick={() => { if (purgeDomain) localPurgeDomainMut.mutate(purgeDomain); }} disabled={!purgeDomain}>
                  Purge Domain
                </Button>
              </div>
              <Button variant="destructive" onClick={() => { if (confirm("Purge ALL local cache?")) localPurgeMut.mutate(); }} disabled={localPurgeMut.isPending}>
                {localPurgeMut.isPending ? "Purging..." : "Purge Everything"}
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {/* ===== CLOUDFLARE CDN SECTION ===== */}
      {status?.cloudflare_cdn && (
        <>
          <h2 className="text-xl font-semibold flex items-center gap-2"><Cloud className="h-5 w-5" /> Cloudflare CDN</h2>

          <div className="max-w-sm">
            <Select value={selectedZone} onValueChange={setSelectedZone}>
              <SelectTrigger><SelectValue placeholder="Select zone" /></SelectTrigger>
              <SelectContent>
                {zones.map((z: Zone) => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {selectedZone && (
            <>
              {analytics && (
                <Card>
                  <CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5" /> Analytics (24h)</CardTitle></CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="rounded-lg bg-muted p-3 text-center">
                        <div className="text-xl font-bold text-emerald-400">{analytics.request_hit_ratio}%</div>
                        <div className="text-xs text-muted-foreground">Hit Ratio</div>
                      </div>
                      <div className="rounded-lg bg-muted p-3 text-center">
                        <div className="text-xl font-bold text-emerald-400">{analytics.bandwidth_hit_ratio}%</div>
                        <div className="text-xs text-muted-foreground">BW Hit Ratio</div>
                      </div>
                      <div className="rounded-lg bg-muted p-3 text-center">
                        <div className="text-xl font-bold">{analytics.cached_bandwidth_mb} MB</div>
                        <div className="text-xs text-muted-foreground">Cached</div>
                      </div>
                      <div className="rounded-lg bg-muted p-3 text-center">
                        <div className="text-xl font-bold">{analytics.total_requests?.toLocaleString()}</div>
                        <div className="text-xs text-muted-foreground">Requests</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {cacheSettings && (
                <Card>
                  <CardHeader><CardTitle className="flex items-center gap-2"><Settings2 className="h-5 w-5" /> Settings</CardTitle></CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Cache Level</Label>
                        <Select value={cacheSettings.cache_level} onValueChange={(v) => updateMut.mutate({ cache_level: v })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="aggressive">Aggressive</SelectItem>
                            <SelectItem value="basic">Basic</SelectItem>
                            <SelectItem value="simplified">Simplified</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Browser TTL</Label>
                        <Select value={String(cacheSettings.browser_cache_ttl)} onValueChange={(v) => updateMut.mutate({ browser_cache_ttl: parseInt(v) })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0">Respect Origin</SelectItem>
                            <SelectItem value="1800">30 min</SelectItem>
                            <SelectItem value="3600">1 hour</SelectItem>
                            <SelectItem value="14400">4 hours</SelectItem>
                            <SelectItem value="86400">1 day</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch checked={cacheSettings.always_online === "on"} onCheckedChange={(v) => updateMut.mutate({ always_online: v })} />
                      <Label>Always Online</Label>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => autoOptMut.mutate()} disabled={autoOptMut.isPending}>
                        <Zap className="mr-2 h-4 w-4" />{autoOptMut.isPending ? "Optimizing..." : "Auto-Optimize"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader><CardTitle>Purge Cloudflare Cache</CardTitle></CardHeader>
                <CardContent>
                  <Button variant="destructive" onClick={() => { if (confirm("Purge ALL Cloudflare cache?")) cfPurgeMut.mutate(); }} disabled={cfPurgeMut.isPending}>
                    {cfPurgeMut.isPending ? "Purging..." : "Purge Everything"}
                  </Button>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}

      {/* No cache info */}
      {status?.active === "none" && (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-muted-foreground">
              No cache system active. Enable cache on individual domains (Domain settings) for local CDN,
              or configure CLOUDFLARE_API_TOKEN for Cloudflare CDN.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
