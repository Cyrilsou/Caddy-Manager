import api from "./client";

export const resolveDns = (hostname: string) => api.get("/dns/resolve", { params: { hostname } });
export const verifyDns = (hostname: string, expectedIp: string) =>
  api.get("/dns/verify", { params: { hostname, expected_ip: expectedIp } });
export const verifyAllDomains = (expectedIp: string) =>
  api.post("/dns/verify-all", null, { params: { expected_ip: expectedIp } });
