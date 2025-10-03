// Login Form Component Tests
// Test ID Prefix: TC-AF-LF

import React from 'react'
import { render, screen, fireEvent, waitFor } from '../utils/test-utils'
import { LoginForm } from '@/components/features/auth/LoginForm'

// Mock Next.js navigation
const mockPush = jest.fn()
const mockReplace = jest.fn()
const mockBack = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: mockPush,
    replace: mockReplace,
    back: mockBack,
    prefetch: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  })),
  usePathname: jest.fn(() => '/'),
  useSearchParams: jest.fn(() => new URLSearchParams()),
}))

// Mock auth store
const mockLogin = jest.fn()
const mockLogout = jest.fn()

jest.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: jest.fn(() => ({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: false,
    login: mockLogin,
    logout: mockLogout,
    setUser: jest.fn(),
    setTokens: jest.fn(),
    clearTokens: jest.fn(),
  })),
}))

describe('LoginForm Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('TC-AF-LF-001: Form Rendering', () => {
    it('should render email input field', () => {
      render(<LoginForm />)
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    })

    it('should render password input field', () => {
      render(<LoginForm />)
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    })

    it('should render remember me checkbox', () => {
      render(<LoginForm />)
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
    })

    it('should render login button', () => {
      render(<LoginForm />)
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render link to register page', () => {
      render(<LoginForm />)
      expect(screen.getByText(/sign up/i)).toBeInTheDocument()
    })

    it('should render forgot password link', () => {
      render(<LoginForm />)
      expect(screen.getByText(/forgot password/i)).toBeInTheDocument()
    })
  })

  describe('TC-AF-LF-002: Password Visibility Toggle', () => {
    it('should hide password by default', () => {
      render(<LoginForm />)
      const passwordInput = screen.getByLabelText(/password/i)
      expect(passwordInput).toHaveAttribute('type', 'password')
    })

    it('should show password when toggle button clicked', () => {
      render(<LoginForm />)
      const toggleButton = screen.getByRole('button', { name: /show password/i })
      const passwordInput = screen.getByLabelText(/password/i)

      fireEvent.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'text')
    })

    it('should toggle password visibility multiple times', () => {
      render(<LoginForm />)
      const toggleButton = screen.getByRole('button', { name: /show password/i })
      const passwordInput = screen.getByLabelText(/password/i)

      fireEvent.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'text')

      fireEvent.click(toggleButton)
      expect(passwordInput).toHaveAttribute('type', 'password')
    })
  })

  describe('TC-AF-LF-003: Form Validation', () => {
    it('should show error for invalid email', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      })
    })

    it('should show error for empty password', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('should clear errors when user fixes input', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // Trigger error
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      })

      // Fix input
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })

      await waitFor(() => {
        expect(screen.queryByText(/invalid email address/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('TC-AF-LF-004: Form Submission', () => {
    it('should call login function with correct credentials', async () => {
      mockLogin.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: false,
        })
      })
    })

    it('should include rememberMe when checkbox is checked', async () => {
      mockLogin.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const rememberMeCheckbox = screen.getByLabelText(/remember me/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(rememberMeCheckbox)
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: true,
        })
      })
    })

    it('should redirect to dashboard on successful login', async () => {
      mockLogin.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
      })
    })

    it('should show error toast on login failure', async () => {
      mockLogin.mockRejectedValue(new Error('Invalid credentials'))

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'WrongPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        // Toast notification should appear
        expect(screen.getByText(/login failed/i)).toBeInTheDocument()
      })
    })
  })

  describe('TC-AF-LF-005: Loading State', () => {
    it('should show loading spinner during submission', async () => {
      ;(useAuthStore as unknown as jest.Mock).mockReturnValue({
        login: mockLogin,
        isLoading: true,
      })

      render(<LoginForm />)

      expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })

    it('should disable form inputs during submission', () => {
      ;(useAuthStore as unknown as jest.Mock).mockReturnValue({
        login: mockLogin,
        isLoading: true,
      })

      render(<LoginForm />)

      expect(screen.getByLabelText(/email/i)).toBeDisabled()
      expect(screen.getByLabelText(/password/i)).toBeDisabled()
      expect(screen.getByLabelText(/remember me/i)).toBeDisabled()
    })
  })

  describe('TC-AF-LF-006: Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<LoginForm />)

      expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('aria-required', 'true')
    })

    it('should associate error messages with inputs', async () => {
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        const error = screen.getByText(/invalid email address/i)
        expect(emailInput).toHaveAttribute('aria-describedby', error.id)
      })
    })
  })
})
