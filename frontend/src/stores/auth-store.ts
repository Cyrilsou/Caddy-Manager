import { create } from "zustand";

interface AuthState {
  username: string | null;
  isAuthenticated: boolean;
  login: (username: string) => void;
  logout: () => void;
}

// Tokens are now in HttpOnly cookies (not accessible from JS).
// We only track auth state and username in the store.
export const useAuthStore = create<AuthState>((set) => ({
  username: localStorage.getItem("username"),
  isAuthenticated: localStorage.getItem("is_authenticated") === "true",

  login: (username) => {
    localStorage.setItem("username", username);
    localStorage.setItem("is_authenticated", "true");
    set({ username, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("username");
    localStorage.removeItem("is_authenticated");
    set({ username: null, isAuthenticated: false });
  },
}));
