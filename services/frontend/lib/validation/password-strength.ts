/**
 * Password strength levels
 */
export enum PasswordStrength {
  WEAK = 0,
  FAIR = 1,
  GOOD = 2,
  STRONG = 3,
}

/**
 * Password strength result
 */
export interface PasswordStrengthResult {
  strength: PasswordStrength;
  label: string;
  color: string;
  percentage: number;
  feedback: string[];
}

/**
 * Calculate password strength based on various criteria
 *
 * @param password - The password to check
 * @returns PasswordStrengthResult with strength level and feedback
 */
export function calculatePasswordStrength(password: string): PasswordStrengthResult {
  if (!password) {
    return {
      strength: PasswordStrength.WEAK,
      label: 'Weak',
      color: 'red',
      percentage: 0,
      feedback: ['Enter a password'],
    };
  }

  let score = 0;
  const feedback: string[] = [];

  // Length check
  if (password.length >= 8) {
    score += 1;
  } else {
    feedback.push('Use at least 8 characters');
  }

  if (password.length >= 12) {
    score += 1;
  }

  // Uppercase letters
  if (/[A-Z]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Add uppercase letters (A-Z)');
  }

  // Lowercase letters
  if (/[a-z]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Add lowercase letters (a-z)');
  }

  // Numbers
  if (/[0-9]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Add numbers (0-9)');
  }

  // Special characters
  if (/[^A-Za-z0-9]/.test(password)) {
    score += 1;
  } else {
    feedback.push('Add special characters (!@#$%^&*)');
  }

  // Check for common patterns (reduce score)
  const commonPatterns = [
    /^123456/,
    /^password/i,
    /^qwerty/i,
    /^abc123/i,
    /^111111/,
  ];

  for (const pattern of commonPatterns) {
    if (pattern.test(password)) {
      score = Math.max(0, score - 2);
      feedback.push('Avoid common patterns like "password123"');
      break;
    }
  }

  // Check for repeated characters (reduce score)
  if (/(.)\1{2,}/.test(password)) {
    score = Math.max(0, score - 1);
    feedback.push('Avoid repeated characters');
  }

  // Determine strength level (0-6 score -> 0-3 strength)
  let strength: PasswordStrength;
  let label: string;
  let color: string;
  let percentage: number;

  if (score <= 2) {
    strength = PasswordStrength.WEAK;
    label = 'Weak';
    color = 'red';
    percentage = 25;
  } else if (score <= 4) {
    strength = PasswordStrength.FAIR;
    label = 'Fair';
    color = 'orange';
    percentage = 50;
  } else if (score <= 5) {
    strength = PasswordStrength.GOOD;
    label = 'Good';
    color = 'yellow';
    percentage = 75;
  } else {
    strength = PasswordStrength.STRONG;
    label = 'Strong';
    color = 'green';
    percentage = 100;
    feedback.push('Great password!');
  }

  return {
    strength,
    label,
    color,
    percentage,
    feedback,
  };
}

/**
 * Check if password meets minimum requirements
 * (at least FAIR strength)
 */
export function meetsMinimumRequirements(password: string): boolean {
  const result = calculatePasswordStrength(password);
  return result.strength >= PasswordStrength.FAIR;
}

/**
 * Get color class for Tailwind CSS based on strength
 */
export function getPasswordStrengthColor(strength: PasswordStrength): string {
  switch (strength) {
    case PasswordStrength.WEAK:
      return 'bg-red-500';
    case PasswordStrength.FAIR:
      return 'bg-orange-500';
    case PasswordStrength.GOOD:
      return 'bg-yellow-500';
    case PasswordStrength.STRONG:
      return 'bg-green-500';
    default:
      return 'bg-gray-300';
  }
}

/**
 * Get text color class for Tailwind CSS based on strength
 */
export function getPasswordStrengthTextColor(strength: PasswordStrength): string {
  switch (strength) {
    case PasswordStrength.WEAK:
      return 'text-red-600';
    case PasswordStrength.FAIR:
      return 'text-orange-600';
    case PasswordStrength.GOOD:
      return 'text-yellow-600';
    case PasswordStrength.STRONG:
      return 'text-green-600';
    default:
      return 'text-gray-600';
  }
}
