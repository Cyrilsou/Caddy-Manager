import api from "./client";

export const verifyToken = () => api.get("/cloudflare/verify");
export const listZones = () => api.get("/cloudflare/zones");
export const listDnsRecords = (zoneId: string) => api.get(`/cloudflare/zones/${zoneId}/dns`);
export const createDnsRecord = (data: Record<string, unknown>) => api.post("/cloudflare/dns", data);
export const updateDnsRecord = (data: Record<string, unknown>) => api.put("/cloudflare/dns", data);
export const deleteDnsRecord = (zoneId: string, recordId: string) =>
  api.delete(`/cloudflare/dns/${zoneId}/${recordId}`);
export const toggleProxy = (data: { zone_id: string; record_id: string; proxied: boolean }) =>
  api.post("/cloudflare/dns/toggle-proxy", data);
export const getSslMode = (zoneId: string) => api.get(`/cloudflare/zones/${zoneId}/ssl`);
export const setSslMode = (zoneId: string, mode: string) =>
  api.patch(`/cloudflare/zones/${zoneId}/ssl`, { mode });
