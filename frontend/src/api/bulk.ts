import api from "./client";

export const bulkCreateDomains = (domains: Record<string, unknown>[]) =>
  api.post("/bulk/domains", { domains });
