// Password Strength Calculator Tests
// Test ID Prefix: TC-SM-PS

import {
  calculatePasswordStrength,
  PasswordStrength,
  meetsMinimumRequirements,
  getPasswordStrengthColor,
  getPasswordStrengthTextColor
} from '@/lib/validation/password-strength'

describe('Password Strength Calculator', () => {
  describe('TC-SM-PS-001: Weak Passwords', () => {
    it('should classify short password as WEAK', () => {
      const result = calculatePasswordStrength('short')
      expect(result.strength).toBe(PasswordStrength.WEAK)
      expect(result.percentage).toBeLessThanOrEqual(25)
    })

    it('should classify simple password as WEAK', () => {
      const result = calculatePasswordStrength('password')
      expect(result.strength).toBe(PasswordStrength.WEAK)
      expect(result.color).toBe('red')
    })

    it('should provide feedback for weak passwords', () => {
      const result = calculatePasswordStrength('abc123')
      expect(result.feedback.length).toBeGreaterThan(0)
      expect(result.feedback.some(f => f.includes('8 characters'))).toBe(true)
    })
  })

  describe('TC-SM-PS-002: Fair Passwords', () => {
    it('should classify password with basic requirements as FAIR', () => {
      const result = calculatePasswordStrength('MySecret1')
      expect(result.strength).toBe(PasswordStrength.FAIR)
      expect(result.percentage).toBe(50)
    })

    it('should show orange color for FAIR passwords', () => {
      const result = calculatePasswordStrength('MySecret1')
      expect(result.color).toBe('orange')
    })
  })

  describe('TC-SM-PS-003: Good Passwords', () => {
    it('should classify password with special chars as GOOD', () => {
      const result = calculatePasswordStrength('MySecret1!')
      expect(result.strength).toBe(PasswordStrength.GOOD)
      expect(result.percentage).toBe(75)
    })

    it('should show yellow color for GOOD passwords', () => {
      const result = calculatePasswordStrength('MySecret1!')
      expect(result.color).toBe('yellow')
    })
  })

  describe('TC-SM-PS-004: Strong Passwords', () => {
    it('should classify complex password as STRONG', () => {
      const result = calculatePasswordStrength('MyLongSecret1!')
      expect(result.strength).toBe(PasswordStrength.STRONG)
      expect(result.percentage).toBe(100)
    })

    it('should show green color for STRONG passwords', () => {
      const result = calculatePasswordStrength('V3ry!Str0ng#Code')
      expect(result.color).toBe('green')
    })

    it('should have Great password feedback for strong passwords', () => {
      const result = calculatePasswordStrength('Ult1m@te!Secur3Key')
      expect(result.feedback).toContain('Great password!')
    })
  })

  describe('TC-SM-PS-005: Special Cases', () => {
    it('should handle empty string', () => {
      const result = calculatePasswordStrength('')
      expect(result.strength).toBe(PasswordStrength.WEAK)
      expect(result.percentage).toBe(0)
      expect(result.feedback).toContain('Enter a password')
    })

    it('should penalize common patterns', () => {
      const weakResult = calculatePasswordStrength('password123')
      const strongResult = calculatePasswordStrength('MyS3cur3!XyZ')
      expect(strongResult.strength).toBeGreaterThan(weakResult.strength)
    })

    it('should penalize repeated characters', () => {
      const repeated = calculatePasswordStrength('aaaaaBBBB1111')
      const varied = calculatePasswordStrength('Ab1Cd2Ef3Gh4!')
      expect(varied.strength).toBeGreaterThanOrEqual(repeated.strength)
    })
  })

  describe('TC-SM-PS-006: Scoring Logic', () => {
    it('should increase strength with length', () => {
      const short = calculatePasswordStrength('Code1!')
      const long = calculatePasswordStrength('MyLongSecret1!')
      expect(long.strength).toBeGreaterThan(short.strength)
    })

    it('should increase strength with character variety', () => {
      const simple = calculatePasswordStrength('mysecret')
      const complex = calculatePasswordStrength('MyS3cr3t!')
      expect(complex.strength).toBeGreaterThan(simple.strength)
    })

    it('should have correct percentage values', () => {
      const weak = calculatePasswordStrength('abc')
      const fair = calculatePasswordStrength('MySecret1')
      const good = calculatePasswordStrength('MySecret1!')
      const strong = calculatePasswordStrength('MyLongSecret1!')

      expect(weak.percentage).toBe(25)
      expect(fair.percentage).toBe(50)
      expect(good.percentage).toBe(75)
      expect(strong.percentage).toBe(100)
    })
  })

  describe('TC-SM-PS-007: Feedback Messages', () => {
    it('should suggest adding uppercase letters', () => {
      const result = calculatePasswordStrength('mysecret123!')
      expect(result.feedback.some(f => f.includes('uppercase'))).toBe(true)
    })

    it('should suggest adding lowercase letters', () => {
      const result = calculatePasswordStrength('MYSECRET123!')
      expect(result.feedback.some(f => f.includes('lowercase'))).toBe(true)
    })

    it('should suggest adding numbers', () => {
      const result = calculatePasswordStrength('MySecret!')
      expect(result.feedback.some(f => f.includes('numbers'))).toBe(true)
    })

    it('should suggest adding special characters', () => {
      const result = calculatePasswordStrength('MySecret123')
      expect(result.feedback.some(f => f.includes('special'))).toBe(true)
    })

    it('should suggest increasing length', () => {
      const result = calculatePasswordStrength('Code1!')
      expect(result.feedback.some(f => f.includes('8 characters'))).toBe(true)
    })
  })

  describe('TC-SM-PS-008: Helper Functions', () => {
    it('should check minimum requirements correctly', () => {
      expect(meetsMinimumRequirements('weak')).toBe(false)
      expect(meetsMinimumRequirements('MySecret1')).toBe(true)
      expect(meetsMinimumRequirements('MySecret1!')).toBe(true)
    })

    it('should return correct Tailwind color classes', () => {
      expect(getPasswordStrengthColor(PasswordStrength.WEAK)).toBe('bg-red-500')
      expect(getPasswordStrengthColor(PasswordStrength.FAIR)).toBe('bg-orange-500')
      expect(getPasswordStrengthColor(PasswordStrength.GOOD)).toBe('bg-yellow-500')
      expect(getPasswordStrengthColor(PasswordStrength.STRONG)).toBe('bg-green-500')
    })

    it('should return correct text color classes', () => {
      expect(getPasswordStrengthTextColor(PasswordStrength.WEAK)).toBe('text-red-600')
      expect(getPasswordStrengthTextColor(PasswordStrength.FAIR)).toBe('text-orange-600')
      expect(getPasswordStrengthTextColor(PasswordStrength.GOOD)).toBe('text-yellow-600')
      expect(getPasswordStrengthTextColor(PasswordStrength.STRONG)).toBe('text-green-600')
    })
  })
})
