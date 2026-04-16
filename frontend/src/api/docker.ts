import api from "./client";

export const listContainers = () => api.get("/docker/containers");
export const getContainer = (name: string) => api.get(`/docker/containers/${name}`);
export const restartContainer = (name: string) => api.post(`/docker/containers/${name}/restart`);
