import api from "./client";

export const listBackends = () => api.get("/backends");

export const getBackend = (id: number) => api.get(`/backends/${id}`);

export const createBackend = (data: Record<string, unknown>) =>
  api.post("/backends", data);

export const updateBackend = (id: number, data: Record<string, unknown>) =>
  api.put(`/backends/${id}`, data);

export const deleteBackend = (id: number) => api.delete(`/backends/${id}`);

export const checkBackendHealth = (id: number) =>
  api.post(`/backends/${id}/health-check`);
