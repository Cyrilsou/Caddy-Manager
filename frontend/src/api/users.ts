import api from "./client";

export const listUsers = () => api.get("/users");
export const createUser = (data: Record<string, unknown>) => api.post("/users", data);
export const updateUser = (id: number, data: Record<string, unknown>) => api.put(`/users/${id}`, data);
export const deleteUser = (id: number) => api.delete(`/users/${id}`);
