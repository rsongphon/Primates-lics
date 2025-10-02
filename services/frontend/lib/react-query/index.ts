/**
 * React Query Index
 * Central export point for all React Query hooks and configuration
 */

export { queryClient, queryKeys } from './query-client';

// Authentication hooks
export {
  useCurrentUser,
  useLogin,
  useRegister,
  useLogout,
  useRefreshToken,
  useRequestPasswordReset,
  useResetPassword,
  useUpdateProfile,
  useChangePassword,
} from './auth-hooks';

// Device hooks
export {
  useDevices,
  useDevice,
  useDeviceTelemetry,
  useCreateDevice,
  useUpdateDevice,
  useDeleteDevice,
  useSendHeartbeat,
  useUpdateDeviceStatus,
  usePostDeviceTelemetry,
} from './device-hooks';
