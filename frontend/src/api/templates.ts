import api from "./client";

export const listTemplates = () => api.get("/templates");
export const createTemplate = (data: Record<string, unknown>) => api.post("/templates", data);
export const deleteTemplate = (id: number) => api.delete(`/templates/${id}`);
