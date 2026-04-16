import api from "./client";

export const listDomains = (params?: { search?: string; is_active?: boolean }) =>
  api.get("/domains", { params });

export const getDomain = (id: number) => api.get(`/domains/${id}`);

export const createDomain = (data: Record<string, unknown>) =>
  api.post("/domains", data);

export const updateDomain = (id: number, data: Record<string, unknown>) =>
  api.put(`/domains/${id}`, data);

export const deleteDomain = (id: number) => api.delete(`/domains/${id}`);

export const toggleDomain = (id: number) => api.post(`/domains/${id}/toggle`);
