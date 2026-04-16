import api from "./client";

export const listAuditLogs = (params?: {
  action?: string;
  resource_type?: string;
  page?: number;
  per_page?: number;
}) => api.get("/audit", { params });
