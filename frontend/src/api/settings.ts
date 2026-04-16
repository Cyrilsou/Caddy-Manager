import api from "./client";

export const listSettings = () => api.get("/settings");
export const updateSetting = (key: string, value: string) =>
  api.put(`/settings/${key}`, { value });
