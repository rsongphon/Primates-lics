'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  registerAccountSchema,
  registerProfileSchema,
  registerOrganizationSchema,
  registerCompleteSchema,
  type RegisterAccountFormData,
  type RegisterProfileFormData,
  type RegisterOrganizationFormData,
  type RegisterCompleteFormData,
} from '@/lib/validation';
import { PasswordStrength } from './PasswordStrength';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';

type RegistrationStep = 1 | 2 | 3;

interface StepData {
  account?: RegisterAccountFormData;
  profile?: RegisterProfileFormData;
  organization?: RegisterOrganizationFormData;
}

export function RegistrationForm() {
  const router = useRouter();
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState<RegistrationStep>(1);
  const [stepData, setStepData] = useState<StepData>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Step 1: Account Creation Form
  const accountForm = useForm<RegisterAccountFormData>({
    resolver: zodResolver(registerAccountSchema),
    defaultValues: stepData.account,
  });

  // Step 2: Profile Information Form
  const profileForm = useForm<RegisterProfileFormData>({
    resolver: zodResolver(registerProfileSchema),
    defaultValues: stepData.profile,
  });

  // Step 3: Organization Setup Form
  const organizationForm = useForm<RegisterOrganizationFormData>({
    resolver: zodResolver(registerOrganizationSchema),
    defaultValues: stepData.organization || {
      joinExisting: false,
    },
  });

  const password = accountForm.watch('password');
  const joinExisting = organizationForm.watch('joinExisting');

  // Handle step 1 submission
  const onAccountSubmit = (data: RegisterAccountFormData) => {
    setStepData((prev) => ({ ...prev, account: data }));
    setCurrentStep(2);
  };

  // Handle step 2 submission
  const onProfileSubmit = (data: RegisterProfileFormData) => {
    setStepData((prev) => ({ ...prev, profile: data }));
    setCurrentStep(3);
  };

  // Handle step 3 submission (final)
  const onOrganizationSubmit = async (data: RegisterOrganizationFormData) => {
    setStepData((prev) => ({ ...prev, organization: data }));

    // Combine all step data
    const completeData: RegisterCompleteFormData = {
      ...stepData.account!,
      ...stepData.profile!,
      ...data,
    };

    try {
      // Validate complete data
      registerCompleteSchema.parse(completeData);

      // TODO: Call registration API
      // const response = await authApi.register(completeData);

      toast({
        title: 'Registration successful',
        description: 'Your account has been created. Please sign in.',
      });

      // Redirect to login
      router.push('/login');
    } catch (error: any) {
      toast({
        title: 'Registration failed',
        description: error?.message || 'An error occurred during registration',
        variant: 'destructive',
      });
    }
  };

  // Navigation
  const goBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as RegistrationStep);
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress Indicator */}
      <div className="flex items-center justify-between">
        {[1, 2, 3].map((step) => (
          <div key={step} className="flex items-center flex-1">
            <div
              className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors ${
                step < currentStep
                  ? 'bg-blue-600 border-blue-600 text-white'
                  : step === currentStep
                  ? 'border-blue-600 text-blue-600'
                  : 'border-gray-300 text-gray-400'
              }`}
            >
              {step < currentStep ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <span className="text-sm font-semibold">{step}</span>
              )}
            </div>
            {step < 3 && (
              <div
                className={`flex-1 h-1 mx-2 transition-colors ${
                  step < currentStep ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Titles */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900">
          {currentStep === 1 && 'Create Account'}
          {currentStep === 2 && 'Profile Information'}
          {currentStep === 3 && 'Organization Setup'}
        </h3>
        <p className="text-sm text-gray-600">
          Step {currentStep} of 3
        </p>
      </div>

      {/* Step 1: Account Creation */}
      {currentStep === 1 && (
        <form onSubmit={accountForm.handleSubmit(onAccountSubmit)} className="space-y-4">
          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              {...accountForm.register('email')}
              className={accountForm.formState.errors.email ? 'border-red-500' : ''}
            />
            {accountForm.formState.errors.email && (
              <p className="text-sm text-red-600">{accountForm.formState.errors.email.message}</p>
            )}
          </div>

          {/* Password */}
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Create a strong password"
                autoComplete="new-password"
                {...accountForm.register('password')}
                className={accountForm.formState.errors.password ? 'border-red-500' : ''}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                )}
              </button>
            </div>
            {accountForm.formState.errors.password && (
              <p className="text-sm text-red-600">{accountForm.formState.errors.password.message}</p>
            )}
            {/* Password Strength Indicator */}
            {password && <PasswordStrength password={password} />}
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm password</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="Re-enter your password"
                autoComplete="new-password"
                {...accountForm.register('confirmPassword')}
                className={accountForm.formState.errors.confirmPassword ? 'border-red-500' : ''}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showConfirmPassword ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                )}
              </button>
            </div>
            {accountForm.formState.errors.confirmPassword && (
              <p className="text-sm text-red-600">{accountForm.formState.errors.confirmPassword.message}</p>
            )}
          </div>

          {/* Next Button */}
          <Button type="submit" className="w-full">
            Next
          </Button>
        </form>
      )}

      {/* Step 2: Profile Information */}
      {currentStep === 2 && (
        <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
          {/* First Name */}
          <div className="space-y-2">
            <Label htmlFor="firstName">First name</Label>
            <Input
              id="firstName"
              type="text"
              placeholder="John"
              autoComplete="given-name"
              {...profileForm.register('firstName')}
              className={profileForm.formState.errors.firstName ? 'border-red-500' : ''}
            />
            {profileForm.formState.errors.firstName && (
              <p className="text-sm text-red-600">{profileForm.formState.errors.firstName.message}</p>
            )}
          </div>

          {/* Last Name */}
          <div className="space-y-2">
            <Label htmlFor="lastName">Last name</Label>
            <Input
              id="lastName"
              type="text"
              placeholder="Doe"
              autoComplete="family-name"
              {...profileForm.register('lastName')}
              className={profileForm.formState.errors.lastName ? 'border-red-500' : ''}
            />
            {profileForm.formState.errors.lastName && (
              <p className="text-sm text-red-600">{profileForm.formState.errors.lastName.message}</p>
            )}
          </div>

          {/* Phone (Optional) */}
          <div className="space-y-2">
            <Label htmlFor="phone">Phone number (optional)</Label>
            <Input
              id="phone"
              type="tel"
              placeholder="+1 (555) 000-0000"
              autoComplete="tel"
              {...profileForm.register('phone')}
              className={profileForm.formState.errors.phone ? 'border-red-500' : ''}
            />
            {profileForm.formState.errors.phone && (
              <p className="text-sm text-red-600">{profileForm.formState.errors.phone.message}</p>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex space-x-3">
            <Button type="button" variant="outline" onClick={goBack} className="flex-1">
              Back
            </Button>
            <Button type="submit" className="flex-1">
              Next
            </Button>
          </div>
        </form>
      )}

      {/* Step 3: Organization Setup */}
      {currentStep === 3 && (
        <form onSubmit={organizationForm.handleSubmit(onOrganizationSubmit)} className="space-y-4">
          {/* Join Existing Organization Toggle */}
          <div className="flex items-center space-x-2">
            <input
              id="joinExisting"
              type="checkbox"
              {...organizationForm.register('joinExisting')}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <Label htmlFor="joinExisting" className="cursor-pointer">
              I want to join an existing organization
            </Label>
          </div>

          {joinExisting ? (
            /* Organization Code Input */
            <div className="space-y-2">
              <Label htmlFor="organizationCode">Organization code</Label>
              <Input
                id="organizationCode"
                type="text"
                placeholder="Enter the code provided by your organization"
                {...organizationForm.register('organizationCode')}
                className={organizationForm.formState.errors.organizationCode ? 'border-red-500' : ''}
              />
              {organizationForm.formState.errors.organizationCode && (
                <p className="text-sm text-red-600">{organizationForm.formState.errors.organizationCode.message}</p>
              )}
              <p className="text-xs text-gray-500">
                Ask your organization administrator for the invitation code
              </p>
            </div>
          ) : (
            /* Organization Name Input */
            <div className="space-y-2">
              <Label htmlFor="organizationName">Organization name</Label>
              <Input
                id="organizationName"
                type="text"
                placeholder="Acme Research Lab"
                {...organizationForm.register('organizationName')}
                className={organizationForm.formState.errors.organizationName ? 'border-red-500' : ''}
              />
              {organizationForm.formState.errors.organizationName && (
                <p className="text-sm text-red-600">{organizationForm.formState.errors.organizationName.message}</p>
              )}
              <p className="text-xs text-gray-500">
                You can invite team members after creating your organization
              </p>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex space-x-3">
            <Button type="button" variant="outline" onClick={goBack} className="flex-1">
              Back
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={organizationForm.formState.isSubmitting}
            >
              {organizationForm.formState.isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating account...
                </span>
              ) : (
                'Create Account'
              )}
            </Button>
          </div>
        </form>
      )}

      {/* Login Link */}
      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500">
          Sign in
        </Link>
      </p>
    </div>
  );
}
