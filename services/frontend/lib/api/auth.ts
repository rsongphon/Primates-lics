/**
 * Authentication API
 * API functions for authentication and user management
 */

import apiClient, { unwrapApiResponse } from './client';
import type { ApiResponse, User } from '@/types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
  organization_id?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

/**
 * Login user
 */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const response = await apiClient.post<ApiResponse<LoginResponse>>('/auth/login', credentials);
  return unwrapApiResponse(response.data);
}

/**
 * Register new user
 */
export async function register(data: RegisterData): Promise<User> {
  const response = await apiClient.post<ApiResponse<User>>('/auth/register', data);
  return unwrapApiResponse(response.data);
}

/**
 * Logout current user
 */
export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout');
  // Clear tokens from storage
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
}

/**
 * Refresh access token
 */
export async function refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
  const response = await apiClient.post<ApiResponse<RefreshTokenResponse>>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return unwrapApiResponse(response.data);
}

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<ApiResponse<User>>('/auth/me');
  return unwrapApiResponse(response.data);
}

/**
 * Update current user profile
 */
export async function updateProfile(data: Partial<User>): Promise<User> {
  const response = await apiClient.patch<ApiResponse<User>>('/auth/me', data);
  return unwrapApiResponse(response.data);
}

/**
 * Change password
 */
export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiClient.post('/auth/change-password', data);
}

/**
 * Request password reset
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post('/auth/forgot-password', { email });
}

/**
 * Reset password with token
 */
export async function resetPassword(data: ResetPasswordRequest): Promise<void> {
  await apiClient.post('/auth/reset-password', data);
}

/**
 * Verify email with token
 */
export async function verifyEmail(token: string): Promise<void> {
  await apiClient.post('/auth/verify-email', { token });
}

/**
 * Resend verification email
 */
export async function resendVerificationEmail(): Promise<void> {
  await apiClient.post('/auth/resend-verification');
}

export const authApi = {
  login,
  register,
  logout,
  refreshToken,
  getCurrentUser,
  updateProfile,
  changePassword,
  requestPasswordReset,
  resetPassword,
  verifyEmail,
  resendVerificationEmail,
};
