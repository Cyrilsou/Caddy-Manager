import api from "./client";

export const listCertificates = () => api.get("/certificates");
export const refreshCertificates = () => api.post("/certificates/refresh");
