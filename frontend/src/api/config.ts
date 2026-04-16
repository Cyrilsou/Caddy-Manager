import api from "./client";

export const getCurrentConfig = () => api.get("/config/current");
export const previewConfig = () => api.get("/config/preview");
export const applyConfig = () => api.post("/config/apply");
export const listVersions = (page = 1) => api.get("/config/versions", { params: { page } });
export const getVersion = (id: number) => api.get(`/config/versions/${id}`);
export const rollbackVersion = (id: number) => api.post(`/config/versions/${id}/rollback`);
export const getVersionDiff = (id: number) => api.get(`/config/versions/${id}/diff`);
export const getCaddyStatus = () => api.get("/config/caddy-status");
