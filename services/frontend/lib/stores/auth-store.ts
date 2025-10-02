/**
 * Auth Store
 * Authentication and authorization state management
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Role, Permission } from '@/types';
import { authApi, type LoginCredentials } from '@/lib/api/auth';

interface AuthState {
  // User data
  user: User | null;
  setUser: (user: User | null) => void;

  // Tokens
  accessToken: string | null;
  refreshToken: string | null;
  rememberMe: boolean;
  setTokens: (accessToken: string, refreshToken: string, rememberMe?: boolean) => void;
  clearTokens: () => void;

  // Authentication status
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Permissions
  permissions: string[];
  roles: Role[];
  setPermissions: (permissions: string[]) => void;
  setRoles: (roles: Role[]) => void;

  // Auth actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  loadUser: () => Promise<void>;
  startTokenRefreshTimer: () => void;
  stopTokenRefreshTimer: () => void;

  // Permission checks
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  hasRole: (roleName: string) => boolean;
  hasAnyRole: (roleNames: string[]) => boolean;
}

// Token refresh timer (stored outside Zustand to avoid serialization issues)
let refreshTimerInterval: NodeJS.Timeout | null = null;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      rememberMe: false,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      permissions: [],
      roles: [],

      // Setters
      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          roles: user?.roles || [],
        }),

      setTokens: (accessToken, refreshToken, rememberMe = false) => {
        set({ accessToken, refreshToken, rememberMe });

        // Store tokens in appropriate storage based on rememberMe preference
        const storage = rememberMe ? localStorage : sessionStorage;
        storage.setItem('access_token', accessToken);
        storage.setItem('refresh_token', refreshToken);

        // Clear from opposite storage to prevent conflicts
        const oppositeStorage = rememberMe ? sessionStorage : localStorage;
        oppositeStorage.removeItem('access_token');
        oppositeStorage.removeItem('refresh_token');

        // Also set cookie for middleware (7 days if remember me, session otherwise)
        const maxAge = rememberMe ? 7 * 24 * 60 * 60 : undefined; // 7 days in seconds
        document.cookie = `access_token=${accessToken}; path=/; ${maxAge ? `max-age=${maxAge};` : ''} SameSite=Lax`;
      },

      clearTokens: () => {
        set({ accessToken: null, refreshToken: null, rememberMe: false });
        // Clear from both storages to be safe
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // Clear cookies
        document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
      },

      setPermissions: (permissions) => set({ permissions }),
      setRoles: (roles) => set({ roles }),

      // Auth actions
      login: async (credentials) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(credentials);
          const { access_token, refresh_token, user } = response;

          // Extract permissions from user roles
          const permissions: string[] = [];
          user.roles?.forEach((role) => {
            role.permissions?.forEach((perm) => {
              const permString = `${perm.resource}:${perm.action}`;
              if (!permissions.includes(permString)) {
                permissions.push(permString);
              }
            });
          });

          // Use rememberMe from credentials (default to false if not provided)
          const rememberMe = credentials.rememberMe ?? false;
          get().setTokens(access_token, refresh_token, rememberMe);

          set({
            user,
            permissions,
            roles: user.roles || [],
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // Start background token refresh timer
          get().startTokenRefreshTimer();
        } catch (error: any) {
          set({
            isLoading: false,
            error: error.error?.message || 'Login failed',
            isAuthenticated: false,
          });
          throw error;
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          get().stopTokenRefreshTimer();
          get().clearTokens();
          set({
            user: null,
            permissions: [],
            roles: [],
            isAuthenticated: false,
            error: null,
          });
        }
      },

      refreshSession: async () => {
        const { refreshToken, rememberMe } = get();
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        try {
          const response = await authApi.refreshToken(refreshToken);
          const storage = rememberMe ? localStorage : sessionStorage;
          storage.setItem('access_token', response.access_token);
          set({ accessToken: response.access_token });
        } catch (error) {
          get().stopTokenRefreshTimer();
          get().logout();
          throw error;
        }
      },

      loadUser: async () => {
        set({ isLoading: true });
        try {
          const user = await authApi.getCurrentUser();

          // Extract permissions
          const permissions: string[] = [];
          user.roles?.forEach((role) => {
            role.permissions?.forEach((perm) => {
              const permString = `${perm.resource}:${perm.action}`;
              if (!permissions.includes(permString)) {
                permissions.push(permString);
              }
            });
          });

          set({
            user,
            permissions,
            roles: user.roles || [],
            isAuthenticated: true,
            isLoading: false,
          });

          // Restart token refresh timer if authenticated
          get().startTokenRefreshTimer();
        } catch (error) {
          set({ isLoading: false });
          get().logout();
          throw error;
        }
      },

      // Token refresh timer management
      startTokenRefreshTimer: () => {
        // Clear existing timer if any
        if (refreshTimerInterval) {
          clearInterval(refreshTimerInterval);
        }

        // Check every minute if token needs refresh
        refreshTimerInterval = setInterval(() => {
          const { accessToken, refreshToken, isAuthenticated } = get();

          if (!isAuthenticated || !accessToken || !refreshToken) {
            get().stopTokenRefreshTimer();
            return;
          }

          try {
            // Decode JWT to check expiry (simple base64 decode)
            const tokenParts = accessToken.split('.');
            if (tokenParts.length !== 3) return;

            const payload = JSON.parse(atob(tokenParts[1]));
            const expiryTime = payload.exp * 1000; // Convert to milliseconds
            const currentTime = Date.now();
            const timeUntilExpiry = expiryTime - currentTime;

            // Refresh token 5 minutes before expiry (300000 ms)
            if (timeUntilExpiry < 300000 && timeUntilExpiry > 0) {
              console.log('Refreshing token before expiry...');
              get().refreshSession().catch((error) => {
                console.error('Auto-refresh failed:', error);
                get().logout();
              });
            }
          } catch (error) {
            console.error('Error checking token expiry:', error);
          }
        }, 60000); // Check every minute
      },

      stopTokenRefreshTimer: () => {
        if (refreshTimerInterval) {
          clearInterval(refreshTimerInterval);
          refreshTimerInterval = null;
        }
      },

      // Permission checks
      hasPermission: (permission) => get().permissions.includes(permission),
      hasAnyPermission: (permissions) =>
        permissions.some((p) => get().permissions.includes(p)),
      hasAllPermissions: (permissions) =>
        permissions.every((p) => get().permissions.includes(p)),
      hasRole: (roleName) => get().roles.some((r) => r.name === roleName),
      hasAnyRole: (roleNames) => roleNames.some((name) => get().hasRole(name)),
    }),
    {
      name: 'lics-auth-storage',
      partialize: (state) => ({
        user: state.user,
        roles: state.roles,
        permissions: state.permissions,
        rememberMe: state.rememberMe,
      }),
    }
  )
);
