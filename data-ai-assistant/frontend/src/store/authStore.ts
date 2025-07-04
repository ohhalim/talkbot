import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  username: string | null;
  login: (token: string, username: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      token: null,
      username: null,
      login: (token: string, username: string) => {
        set({ isAuthenticated: true, token, username });
      },
      logout: () => {
        set({ isAuthenticated: false, token: null, username: null });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);