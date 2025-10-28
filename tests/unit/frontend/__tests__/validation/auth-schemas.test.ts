// Authentication Validation Schemas Tests
// Test ID Prefix: TC-SM-VS

import {
  loginSchema,
  registerAccountSchema,
  registerProfileSchema,
  registerOrganizationSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  changePasswordSchema,
  updateProfileSchema,
} from '@/lib/validation/auth-schemas'

describe('Authentication Validation Schemas', () => {
  describe('TC-SM-VS-001: Login Schema', () => {
    it('should validate correct login credentials', () => {
      const validData = {
        email: 'test@example.com',
        password: 'ValidPass123!',
        rememberMe: true,
      }

      const result = loginSchema.safeParse(validData)
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data).toEqual(validData)
      }
    })

    it('should reject invalid email format', () => {
      const invalidData = {
        email: 'not-an-email',
        password: 'ValidPass123!',
      }

      const result = loginSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].path).toContain('email')
      }
    })

    it('should reject empty password', () => {
      const invalidData = {
        email: 'test@example.com',
        password: '',
      }

      const result = loginSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })

    it('should have optional rememberMe field', () => {
      const dataWithoutRememberMe = {
        email: 'test@example.com',
        password: 'ValidPass123!',
      }

      const result = loginSchema.safeParse(dataWithoutRememberMe)
      expect(result.success).toBe(true)
    })
  })

  describe('TC-SM-VS-002: Register Account Schema', () => {
    it('should validate strong password', () => {
      const validData = {
        email: 'newuser@example.com',
        password: 'StrongPass123!@#',
        confirmPassword: 'StrongPass123!@#',
      }

      const result = registerAccountSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should reject weak password (too short)', () => {
      const invalidData = {
        email: 'newuser@example.com',
        password: 'Short1!',
        confirmPassword: 'Short1!',
      }

      const result = registerAccountSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].message).toContain('at least 8 characters')
      }
    })

    it('should reject password without uppercase', () => {
      const invalidData = {
        email: 'newuser@example.com',
        password: 'lowercase123!',
        confirmPassword: 'lowercase123!',
      }

      const result = registerAccountSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })

    it('should reject password without number', () => {
      const invalidData = {
        email: 'newuser@example.com',
        password: 'NoNumbers!',
        confirmPassword: 'NoNumbers!',
      }

      const result = registerAccountSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })

    it('should reject mismatched passwords', () => {
      const invalidData = {
        email: 'newuser@example.com',
        password: 'ValidPass123!',
        confirmPassword: 'DifferentPass123!',
      }

      const result = registerAccountSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
      if (!result.success) {
        expect(result.error.issues[0].message).toContain('Passwords do not match')
      }
    })
  })

  describe('TC-SM-VS-003: Register Profile Schema', () => {
    it('should validate complete profile', () => {
      const validData = {
        firstName: 'John',
        lastName: 'Doe',
        phone: '+1234567890',
      }

      const result = registerProfileSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should accept profile without optional phone', () => {
      const validData = {
        firstName: 'John',
        lastName: 'Doe',
      }

      const result = registerProfileSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should reject empty names', () => {
      const invalidData = {
        firstName: '',
        lastName: 'Doe',
      }

      const result = registerProfileSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })
  })

  describe('TC-SM-VS-004: Register Organization Schema', () => {
    it('should validate new organization creation', () => {
      const validData = {
        joinExisting: false,
        organizationName: 'My Lab',
      }

      const result = registerOrganizationSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should validate joining existing organization', () => {
      const validData = {
        joinExisting: true,
        organizationCode: 'ABC123XYZ',
      }

      const result = registerOrganizationSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should reject create without organization name', () => {
      const invalidData = {
        joinExisting: false,
      }

      const result = registerOrganizationSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })

    it('should reject join without organization code', () => {
      const invalidData = {
        joinExisting: true,
      }

      const result = registerOrganizationSchema.safeParse(invalidData)
      expect(result.success).toBe(false)
    })
  })

  describe('TC-SM-VS-005: Password Reset Schemas', () => {
    it('should validate forgot password request', () => {
      const validData = {
        email: 'user@example.com',
      }

      const result = forgotPasswordSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should validate password reset with token', () => {
      const validData = {
        token: 'reset-token-123',
        password: 'NewPassword123!',
        confirmPassword: 'NewPassword123!',
      }

      const result = resetPasswordSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should validate password change', () => {
      const validData = {
        currentPassword: 'OldPassword123!',
        newPassword: 'NewPassword123!',
        confirmNewPassword: 'NewPassword123!',
      }

      const result = changePasswordSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })
  })

  describe('TC-SM-VS-006: Update Profile Schema', () => {
    it('should validate profile update', () => {
      const validData = {
        firstName: 'Jane',
        lastName: 'Smith',
        email: 'jane.smith@example.com',
        phone: '+9876543210',
      }

      const result = updateProfileSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('should accept updates with all required fields', () => {
      const validData = {
        firstName: 'Jane',
        lastName: 'Doe',
        email: 'jane.doe@example.com',
      }

      const result = updateProfileSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })
  })
})
