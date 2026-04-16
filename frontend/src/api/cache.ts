import api from "./client";

export const runSpeedTest = () => api.post("/cache/speedtest");
export const purgeAll = (zoneId: string) => api.post(`/cache/purge/all?zone_id=${zoneId}`);
export const purgeUrls = (zoneId: string, urls: string[]) => api.post("/cache/purge/urls", { zone_id: zoneId, urls });
export const purgeHosts = (zoneId: string, hosts: string[]) => api.post("/cache/purge/hosts", { zone_id: zoneId, hosts });
export const getCacheSettings = (zoneId: string) => api.get(`/cache/settings/${zoneId}`);
export const updateCacheSettings = (zoneId: string, data: Record<string, unknown>) => api.patch(`/cache/settings/${zoneId}`, data);
export const autoOptimize = (zoneId: string) => api.post(`/cache/auto-optimize/${zoneId}`);
export const getCacheAnalytics = (zoneId: string) => api.get(`/cache/analytics/${zoneId}`);
