/**
 * Custom Hooks Index
 * Central export point for all custom React hooks
 */

export { useDebounce } from './use-debounce';
export { usePagination } from './use-pagination';
export type { PaginationState, PaginationActions, UsePaginationReturn } from './use-pagination';

export {
  useMediaQuery,
  useIsMobile,
  useIsTablet,
  useIsDesktop,
  useIsDarkMode,
} from './use-media-query';

export { useLocalStorage } from './use-local-storage';

export {
  usePermissions,
  useHasPermission,
  useHasAnyPermission,
  useHasAllPermissions,
  useHasRole,
  useHasAnyRole,
  useCanReadDevices,
  useCanWriteDevices,
  useCanDeleteDevices,
  useCanReadExperiments,
  useCanWriteExperiments,
  useCanDeleteExperiments,
  useCanReadPrimates,
  useCanWritePrimates,
  useCanDeletePrimates,
  useIsAdmin,
  useIsSuperAdmin,
} from './use-permissions';

export {
  useBreadcrumbs,
  createBreadcrumbs,
  getEntityBreadcrumbs,
} from './use-breadcrumbs';
export type { BreadcrumbItem } from './use-breadcrumbs';

export { useNotifications } from './use-notifications';
export type { NotificationOptions } from './use-notifications';

export { useTheme } from './use-theme';
export type { Theme } from './use-theme';
