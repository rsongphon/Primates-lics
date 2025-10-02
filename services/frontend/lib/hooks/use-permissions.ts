/**
 * usePermissions Hook
 * Check user permissions and roles
 */

import { useAuthStore } from '@/lib/stores';

/**
 * Hook for checking user permissions and roles
 */
export function usePermissions() {
  const {
    permissions,
    roles,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
  } = useAuthStore();

  return {
    permissions,
    roles,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
  };
}

/**
 * Hook to check if user has a specific permission
 */
export function useHasPermission(permission: string): boolean {
  const { hasPermission } = useAuthStore();
  return hasPermission(permission);
}

/**
 * Hook to check if user has any of the specified permissions
 */
export function useHasAnyPermission(permissions: string[]): boolean {
  const { hasAnyPermission } = useAuthStore();
  return hasAnyPermission(permissions);
}

/**
 * Hook to check if user has all of the specified permissions
 */
export function useHasAllPermissions(permissions: string[]): boolean {
  const { hasAllPermissions } = useAuthStore();
  return hasAllPermissions(permissions);
}

/**
 * Hook to check if user has a specific role
 */
export function useHasRole(roleName: string): boolean {
  const { hasRole } = useAuthStore();
  return hasRole(roleName);
}

/**
 * Hook to check if user has any of the specified roles
 */
export function useHasAnyRole(roleNames: string[]): boolean {
  const { hasAnyRole } = useAuthStore();
  return hasAnyRole(roleNames);
}

/**
 * Resource-specific permission hooks
 */
export function useCanReadDevices(): boolean {
  return useHasPermission('devices:read');
}

export function useCanWriteDevices(): boolean {
  return useHasPermission('devices:write');
}

export function useCanDeleteDevices(): boolean {
  return useHasPermission('devices:delete');
}

export function useCanReadExperiments(): boolean {
  return useHasPermission('experiments:read');
}

export function useCanWriteExperiments(): boolean {
  return useHasPermission('experiments:write');
}

export function useCanDeleteExperiments(): boolean {
  return useHasPermission('experiments:delete');
}

export function useCanReadPrimates(): boolean {
  return useHasPermission('primates:read');
}

export function useCanWritePrimates(): boolean {
  return useHasPermission('primates:write');
}

export function useCanDeletePrimates(): boolean {
  return useHasPermission('primates:delete');
}

export function useIsAdmin(): boolean {
  return useHasAnyRole(['admin', 'lab_admin', 'super_admin']);
}

export function useIsSuperAdmin(): boolean {
  return useHasRole('super_admin');
}
