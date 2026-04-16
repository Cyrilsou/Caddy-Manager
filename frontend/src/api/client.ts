import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,  // Send HttpOnly cookies automatically
});

// No Bearer header needed — tokens are in HttpOnly cookies

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Refresh uses the HttpOnly refresh_token cookie automatically
        await axios.post("/api/v1/auth/refresh", {}, { withCredentials: true });
        // Retry the original request (new access_token cookie is set)
        return api(originalRequest);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default api;
