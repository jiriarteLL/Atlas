import { create } from 'zustand';

export interface MeUser {
  id: string;
  email: string;
  display_name: string;
  is_platform_admin: boolean;
  active_company: { id: string; name: string; slug: string } | null;
  companies: Array<{ id: string; name: string; slug: string; subdomain: string; roles: string[]; is_active: boolean }>;
  roles_in_active_company: string[];
  permissions_in_active_company: string[];
}

interface AuthState {
  user: MeUser | null;
  loading: boolean;
  setUser: (u: MeUser | null) => void;
  setLoading: (b: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (u) => set({ user: u, loading: false }),
  setLoading: (b) => set({ loading: b }),
  logout: () => {
    localStorage.removeItem('maestro.access_token');
    set({ user: null });
  },
}));
