function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const initialKey = typeof window !== "undefined"
  ? (sessionStorage.getItem("admin_key") || getCookie("admin_key"))
  : null;

import { create } from "zustand";

interface AuthState {
  adminKey: string | null;
  setKey: (key: string) => void;
  clearKey: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  adminKey: initialKey,
  setKey: (key: string) => {
    sessionStorage.setItem("admin_key", key);
    set({ adminKey: key });
  },
  clearKey: () => {
    sessionStorage.removeItem("admin_key");
    document.cookie = "admin_key=; path=/; max-age=0";
    set({ adminKey: null });
  },
  isAuthenticated: () => {
    const key = get().adminKey;
    return key !== null && key.length > 0;
  },
}));
