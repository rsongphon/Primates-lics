// Login Form Component Tests
// Test ID Prefix: TC-AF-LF

import React from 'react'
import { render, screen, fireEvent, waitFor } from '../utils/test-utils'
import userEvent from '@testing-library/user-event'
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

// Mock toast hook
const mockToast = jest.fn()

jest.mock('@/hooks/use-toast', () => ({
  useToast: jest.fn(() => ({
    toast: mockToast,
  })),
}))

// Mock React Query auth hooks
const mockLoginMutation = {
  mutateAsync: jest.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
}

jest.mock('@/lib/react-query', () => ({
  useLogin: jest.fn(() => mockLoginMutation),
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
    // Reset mutation state
    mockLoginMutation.mutateAsync = jest.fn()
    mockLoginMutation.isPending = false
    mockLoginMutation.isError = false
    mockLoginMutation.isSuccess = false
    mockLoginMutation.error = null
  })

  describe('TC-AF-LF-001: Form Rendering', () => {
    it('should render email input field', () => {
      render(<LoginForm />)
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    })

    it('should render password input field', () => {
      render(<LoginForm />)
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument()
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
      expect(screen.getByText(/create one now/i)).toBeInTheDocument()
    })

    it('should render forgot password link', () => {
      render(<LoginForm />)
      expect(screen.getByText(/forgot password/i)).toBeInTheDocument()
    })
  })

  describe('TC-AF-LF-002: Password Visibility Toggle', () => {
    it('should hide password by default', () => {
      render(<LoginForm />)
      const passwordInput = screen.getByPlaceholderText('Enter your password') as HTMLInputElement
      expect(passwordInput.type).toBe('password')
    })

    it('should show password when toggle button clicked', () => {
      render(<LoginForm />)
      const toggleButton = screen.getByLabelText(/show password/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password') as HTMLInputElement

      fireEvent.click(toggleButton)
      expect(passwordInput.type).toBe('text')
    })

    it('should toggle password visibility multiple times', () => {
      render(<LoginForm />)
      const passwordInput = screen.getByPlaceholderText('Enter your password') as HTMLInputElement

      // Initially hidden
      expect(passwordInput.type).toBe('password')

      // Find and click show button
      const showButton = screen.getByLabelText(/show password/i)
      fireEvent.click(showButton)
      expect(passwordInput.type).toBe('text')

      // Find and click hide button (aria-label changed)
      const hideButton = screen.getByLabelText(/hide password/i)
      fireEvent.click(hideButton)
      expect(passwordInput.type).toBe('password')
    })
  })

  describe('TC-AF-LF-003: Form Validation', () => {
    it('should show error for invalid email', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should show error for empty password', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('should clear errors when user fixes input', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // Trigger error
      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
      }, { timeout: 3000 })

      // Fix input and resubmit
      await user.clear(emailInput)
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'ValidPass123!')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.queryByText(/invalid email address/i)).not.toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('TC-AF-LF-004: Form Submission', () => {
    it('should call login function with correct credentials', async () => {
      mockLoginMutation.mutateAsync.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLoginMutation.mutateAsync).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: false,
        })
      })
    })

    it('should include rememberMe when checkbox is checked', async () => {
      mockLoginMutation.mutateAsync.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const rememberMeCheckbox = screen.getByLabelText(/remember me/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(rememberMeCheckbox)
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLoginMutation.mutateAsync).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'ValidPass123!',
          rememberMe: true,
        })
      })
    })

    it('should redirect to dashboard on successful login', async () => {
      mockLoginMutation.mutateAsync.mockResolvedValue(undefined)

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard')
      })
    })

    it('should show error toast on login failure', async () => {
      mockLoginMutation.mutateAsync.mockRejectedValue(new Error('Invalid credentials'))

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'WrongPass123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        // Toast notification should be called
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Login failed',
            variant: 'destructive',
          })
        )
      })
    })
  })

  describe('TC-AF-LF-005: Loading State', () => {
    it('should show loading spinner during submission', async () => {
      // Set isPending to true to simulate loading state
      mockLoginMutation.isPending = true
      mockLoginMutation.mutateAsync.mockImplementation(() => new Promise(() => {})) // Never resolves

      render(<LoginForm />)

      // When isPending is true, button shows "Signing in..." instead of "Sign in"
      const submitButton = screen.getByRole('button', { name: /signing in/i })

      expect(submitButton).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
    })

    it('should disable form inputs during submission', async () => {
      // Simulate a slow async operation
      mockLoginMutation.mutateAsync.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      )

      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByPlaceholderText('Enter your password')
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } })
      fireEvent.click(submitButton)

      // Check that button is disabled during submission
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })
  })

  describe('TC-AF-LF-006: Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<LoginForm />)

      expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByPlaceholderText('Enter your password')).toHaveAttribute('aria-required', 'true')
    })

    it('should associate error messages with inputs', async () => {
      const user = userEvent.setup()
      render(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      await waitFor(() => {
        const error = screen.getByText(/invalid email address/i)
        expect(emailInput).toHaveAttribute('aria-describedby', 'email-error')
      }, { timeout: 3000 })
    })
  })
})
