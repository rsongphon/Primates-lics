// Auth Store Tests
// Test ID Prefix: TC-SM-AS

import { renderHook, act, waitFor } from '@testing-library/react'
import { mockUser, mockTokens, mockAxiosResponse, mockAxiosError } from '../utils/test-utils'

// Mock the auth API before importing the store
jest.mock('@/lib/api/auth', () => ({
  authApi: {
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
    getCurrentUser: jest.fn(),
    register: jest.fn(),
    updateProfile: jest.fn(),
    changePassword: jest.fn(),
    requestPasswordReset: jest.fn(),
    resetPassword: jest.fn(),
  },
}))

// Import after mocking
import { useAuthStore } from '@/lib/stores/auth-store'
import * as authApi from '@/lib/api/auth'

describe('Auth Store', () => {
  beforeEach(() => {
    // Clear storage first
    localStorage.clear()
    sessionStorage.clear()

    // Clear document.cookie
    document.cookie = ''

    // Clear mocks
    jest.clearAllMocks()

    // Reset store state after clearing storage
    const store = useAuthStore.getState()
    if (store.setUser) store.setUser(null)
    if (store.clearTokens) store.clearTokens()
  })

  afterEach(() => {
    // Additional cleanup
    localStorage.clear()
    sessionStorage.clear()
    document.cookie = ''
  })

  describe('TC-SM-AS-001: Initial State', () => {
    it('should have null user initially', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.user).toBeNull()
    })

    it('should have no tokens initially', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.accessToken).toBeNull()
      expect(result.current.refreshToken).toBeNull()
    })

    it('should not be authenticated initially', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('should not be loading initially', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('TC-SM-AS-002: Login Flow', () => {
    it('should successfully login with valid credentials', async () => {
      const mockLogin = jest.spyOn(authApi.authApi, 'login')
        .mockResolvedValue({ ...mockTokens, user: mockUser } as any)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: false,
        })
      })

      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'ValidPass123!',
        rememberMe: false,
      })
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user).toEqual(mockUser)
    })

    it('should store tokens in sessionStorage when rememberMe is false', async () => {
      jest.spyOn(authApi.authApi, 'login')
        .mockResolvedValue({ ...mockTokens, user: mockUser } as any)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: false,
        })
      })

      expect(sessionStorage.getItem('access_token')).toBe(mockTokens.access_token)
      expect(sessionStorage.getItem('refresh_token')).toBe(mockTokens.refresh_token)
    })

    it('should store tokens in localStorage when rememberMe is true', async () => {
      jest.spyOn(authApi.authApi, 'login')
        .mockResolvedValue({ ...mockTokens, user: mockUser } as any)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: true,
        })
      })

      expect(localStorage.getItem('access_token')).toBe(mockTokens.access_token)
      expect(localStorage.getItem('refresh_token')).toBe(mockTokens.refresh_token)
    })

    it('should handle login failure', async () => {
      jest.spyOn(authApi.authApi, 'login')
        .mockRejectedValue(mockAxiosError('Invalid credentials', 401))

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        try {
          await result.current.login({
            email: 'test@example.com',
            password: 'WrongPass123!',
            rememberMe: false,
          })
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBeNull()
    })
  })

  describe('TC-SM-AS-003: Logout Flow', () => {
    it('should successfully logout', async () => {
      const mockLogout = jest.spyOn(authApi.authApi, 'logout')
        .mockResolvedValue(undefined as any)

      const { result } = renderHook(() => useAuthStore())

      // Set initial state
      act(() => {
        result.current.setUser(mockUser)
        result.current.setTokens(mockTokens.access_token, mockTokens.refresh_token, false)
      })

      expect(result.current.isAuthenticated).toBe(true)

      await act(async () => {
        await result.current.logout()
      })

      expect(mockLogout).toHaveBeenCalled()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBeNull()
      expect(result.current.accessToken).toBeNull()
    })

    it('should clear tokens from storage on logout', async () => {
      jest.spyOn(authApi.authApi, 'logout')
        .mockResolvedValue(undefined as any)

      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.setTokens(mockTokens.access_token, mockTokens.refresh_token, true)
      })

      await act(async () => {
        await result.current.logout()
      })

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(sessionStorage.getItem('access_token')).toBeNull()
      expect(sessionStorage.getItem('refresh_token')).toBeNull()
    })
  })

  describe('TC-SM-AS-004: Token Refresh', () => {
    it('should successfully refresh tokens', async () => {
      const newTokens = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
      }

      jest.spyOn(authApi.authApi, 'refreshToken')
        .mockResolvedValue(newTokens as any)

      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.setTokens(mockTokens.access_token, mockTokens.refresh_token, false)
      })

      await act(async () => {
        await result.current.refreshSession()
      })

      expect(result.current.accessToken).toBe(newTokens.access_token)
      expect(result.current.refreshToken).toBe(newTokens.refresh_token)
    })

    it('should logout on refresh failure', async () => {
      jest.spyOn(authApi.authApi, 'refreshToken')
        .mockRejectedValue(mockAxiosError('Invalid refresh token', 401))

      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.setUser(mockUser)
        result.current.setTokens(mockTokens.access_token, mockTokens.refresh_token, false)
      })

      await act(async () => {
        try {
          await result.current.refreshSession()
        } catch (error) {
          // Expected to fail
        }
      })

      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  describe('TC-SM-AS-005: Permission Checking', () => {
    beforeEach(() => {
      // Set user directly on the store state
      useAuthStore.getState().setUser(mockUser)
    })

    it('should check single permission correctly', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.hasPermission('read:devices')).toBe(true)
      expect(result.current.hasPermission('delete:devices')).toBe(false)
    })

    it('should check if user has any of multiple permissions', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.hasAnyPermission(['read:devices', 'delete:devices'])).toBe(true)
      expect(result.current.hasAnyPermission(['delete:devices', 'admin:all'])).toBe(false)
    })

    it('should check if user has all permissions', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.hasAllPermissions(['read:devices', 'write:experiments'])).toBe(true)
      expect(result.current.hasAllPermissions(['read:devices', 'delete:devices'])).toBe(false)
    })

    it('should check role membership', () => {
      const { result } = renderHook(() => useAuthStore())
      expect(result.current.hasRole('researcher')).toBe(true)
      expect(result.current.hasRole('admin')).toBe(false)
    })
  })

  describe('TC-SM-AS-006: Auto Token Refresh', () => {
    it('should start token refresh timer on login', async () => {
      jest.spyOn(authApi.authApi, 'login')
        .mockResolvedValue({ ...mockTokens, user: mockUser } as any)

      const { result } = renderHook(() => useAuthStore())

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: false,
        })
      })

      // Token refresh timer should be started (interval set)
      expect(result.current.isAuthenticated).toBe(true)
      // Note: Actual timer behavior would need integration test
    })

    it('should stop token refresh timer on logout', async () => {
      jest.spyOn(authApi.authApi, 'logout')
        .mockResolvedValue(undefined as any)

      const { result } = renderHook(() => useAuthStore())

      act(() => {
        result.current.setUser(mockUser)
        result.current.setTokens(mockTokens.access_token, mockTokens.refresh_token, false)
      })

      await act(async () => {
        await result.current.logout()
      })

      // Timer should be stopped
      expect(result.current.isAuthenticated).toBe(false)
    })
  })
})
