import { z } from 'zod';

/**
 * Password validation rules:
 * - At least 8 characters
 * - At least one uppercase letter
 * - At least one lowercase letter
 * - At least one number
 * - At least one special character
 */
const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character');

/**
 * Email validation
 */
const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .email('Invalid email address');

/**
 * Login form schema
 */
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().default(false),
});

export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Registration form schema - Step 1 (Account)
 */
export const registerAccountSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export type RegisterAccountData = z.infer<typeof registerAccountSchema>;

/**
 * Registration form schema - Step 2 (Profile)
 */
export const registerProfileSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50, 'First name is too long'),
  lastName: z.string().min(1, 'Last name is required').max(50, 'Last name is too long'),
  phone: z.string().optional(),
});

export type RegisterProfileData = z.infer<typeof registerProfileSchema>;

/**
 * Registration form schema - Step 3 (Organization)
 */
export const registerOrganizationSchema = z.object({
  organizationName: z.string().min(1, 'Organization name is required').max(100),
  joinExisting: z.boolean().default(false),
  organizationCode: z.string().optional(),
}).refine(
  (data) => {
    // If joining existing organization, code is required
    if (data.joinExisting && !data.organizationCode) {
      return false;
    }
    return true;
  },
  {
    message: 'Organization code is required when joining an existing organization',
    path: ['organizationCode'],
  }
);

export type RegisterOrganizationData = z.infer<typeof registerOrganizationSchema>;

/**
 * Complete registration data (all steps combined)
 */
export const registerCompleteSchema = registerAccountSchema
  .merge(registerProfileSchema)
  .merge(registerOrganizationSchema);

export type RegisterCompleteData = z.infer<typeof registerCompleteSchema>;

/**
 * Forgot password schema
 */
export const forgotPasswordSchema = z.object({
  email: emailSchema,
});

export type ForgotPasswordData = z.infer<typeof forgotPasswordSchema>;

/**
 * Reset password schema
 */
export const resetPasswordSchema = z.object({
  password: passwordSchema,
  confirmPassword: z.string().min(1, 'Please confirm your password'),
  token: z.string().min(1, 'Reset token is required'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export type ResetPasswordData = z.infer<typeof resetPasswordSchema>;

/**
 * Change password schema (for authenticated users)
 */
export const changePasswordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: passwordSchema,
  confirmNewPassword: z.string().min(1, 'Please confirm your new password'),
}).refine((data) => data.newPassword === data.confirmNewPassword, {
  message: 'Passwords do not match',
  path: ['confirmNewPassword'],
}).refine((data) => data.currentPassword !== data.newPassword, {
  message: 'New password must be different from current password',
  path: ['newPassword'],
});

export type ChangePasswordData = z.infer<typeof changePasswordSchema>;

/**
 * Update profile schema
 */
export const updateProfileSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50),
  lastName: z.string().min(1, 'Last name is required').max(50),
  email: emailSchema,
  phone: z.string().optional(),
});

export type UpdateProfileData = z.infer<typeof updateProfileSchema>;
