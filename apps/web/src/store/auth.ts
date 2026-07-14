import { create } from "zustand";

interface AuthState {
  adminKey: string | null;
  setKey: (key: string) => void;
  clearKey: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  adminKey: typeof window !== "undefined" ? sessionStorage.getItem("admin_key") : null,
  setKey: (key: string) => {
    sessionStorage.setItem("admin_key", key);
    set({ adminKey: key });
  },
  clearKey: () => {
    sessionStorage.removeItem("admin_key");
    set({ adminKey: null });
  },
  isAuthenticated: () => {
    const key = get().adminKey;
    return key !== null && key.length > 0;
  },
}));
