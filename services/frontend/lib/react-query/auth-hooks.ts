/**
 * Authentication React Query Hooks
 * Query and mutation hooks for authentication operations
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, type LoginCredentials, type RegisterData } from '@/lib/api/auth';
import { useAuthStore } from '@/lib/stores';
import { queryKeys } from './query-client';
import type { User } from '@/types';

/**
 * Query: Get current authenticated user
 */
export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: queryKeys.auth.currentUser,
    queryFn: authApi.getCurrentUser,
    enabled: isAuthenticated, // Only fetch if authenticated
    staleTime: 10 * 60 * 1000, // Consider fresh for 10 minutes
  });
}

/**
 * Mutation: Login
 */
export function useLogin() {
  const queryClient = useQueryClient();
  const { setUser, setTokens, setPermissions, setRoles } = useAuthStore();

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => authApi.login(credentials),
    onSuccess: (response) => {
      const { access_token, refresh_token, user } = response;

      // Extract permissions from roles
      const permissions: string[] = [];
      user.roles?.forEach((role) => {
        role.permissions?.forEach((perm) => {
          const permString = `${perm.resource}:${perm.action}`;
          if (!permissions.includes(permString)) {
            permissions.push(permString);
          }
        });
      });

      // Update auth store
      setTokens(access_token, refresh_token);
      setUser(user);
      setPermissions(permissions);
      setRoles(user.roles || []);

      // Set cached user data
      queryClient.setQueryData(queryKeys.auth.currentUser, user);
    },
    onError: (error: any) => {
      console.error('Login error:', error);
    },
  });
}

/**
 * Mutation: Register
 */
export function useRegister() {
  const queryClient = useQueryClient();
  const { setUser, setTokens, setPermissions, setRoles } = useAuthStore();

  return useMutation({
    mutationFn: (data: RegisterData) => authApi.register(data),
    onSuccess: (response) => {
      const { access_token, refresh_token, user } = response;

      // Extract permissions from roles
      const permissions: string[] = [];
      user.roles?.forEach((role) => {
        role.permissions?.forEach((perm) => {
          const permString = `${perm.resource}:${perm.action}`;
          if (!permissions.includes(permString)) {
            permissions.push(permString);
          }
        });
      });

      // Update auth store
      setTokens(access_token, refresh_token);
      setUser(user);
      setPermissions(permissions);
      setRoles(user.roles || []);

      // Set cached user data
      queryClient.setQueryData(queryKeys.auth.currentUser, user);
    },
  });
}

/**
 * Mutation: Logout
 */
export function useLogout() {
  const queryClient = useQueryClient();
  const { clearTokens, setUser, setPermissions, setRoles } = useAuthStore();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      // Clear auth store
      clearTokens();
      setUser(null);
      setPermissions([]);
      setRoles([]);

      // Clear all cached data
      queryClient.clear();
    },
  });
}

/**
 * Mutation: Refresh token
 */
export function useRefreshToken() {
  const { setTokens } = useAuthStore();

  return useMutation({
    mutationFn: (refreshToken: string) => authApi.refreshToken(refreshToken),
    onSuccess: (response) => {
      sessionStorage.setItem('access_token', response.access_token);
      // Update store if needed (Zustand store already has access token)
    },
  });
}

/**
 * Mutation: Request password reset
 */
export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) => authApi.requestPasswordReset(email),
  });
}

/**
 * Mutation: Reset password
 */
export function useResetPassword() {
  return useMutation({
    mutationFn: (data: { token: string; password: string }) =>
      authApi.resetPassword(data.token, data.password),
  });
}

/**
 * Mutation: Update profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { setUser } = useAuthStore();

  return useMutation({
    mutationFn: (data: { name?: string; email?: string }) => authApi.updateProfile(data),
    onSuccess: (updatedUser) => {
      // Update cached user data
      queryClient.setQueryData(queryKeys.auth.currentUser, updatedUser);

      // Update auth store
      setUser(updatedUser);
    },
  });
}

/**
 * Mutation: Change password
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      authApi.changePassword(data.current_password, data.new_password),
  });
}
