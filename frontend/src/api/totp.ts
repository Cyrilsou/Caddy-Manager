import api from "./client";

export const getTotpStatus = () => api.get("/auth/totp/status");
export const setupTotp = () => api.post("/auth/totp/setup");
export const confirmTotp = (code: string) => api.post("/auth/totp/confirm", { code });
export const disableTotp = (code: string) => api.post("/auth/totp/disable", { code });
