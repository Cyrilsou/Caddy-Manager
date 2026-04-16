import api from "./client";

export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password });

export const getMe = () => api.get("/auth/me");

export const changePassword = (currentPassword: string, newPassword: string) =>
  api.put("/auth/password", { current_password: currentPassword, new_password: newPassword });
