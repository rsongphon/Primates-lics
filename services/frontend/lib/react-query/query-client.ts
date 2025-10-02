/**
 * React Query Client Configuration
 * Centralized configuration for data fetching and caching
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time: data considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,

      // Cache time: unused data kept in cache for 10 minutes
      gcTime: 10 * 60 * 1000,

      // Retry failed requests 3 times with exponential backoff
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),

      // Refetch on window focus for critical data
      refetchOnWindowFocus: true,

      // Refetch on reconnect
      refetchOnReconnect: true,

      // Don't refetch on mount if data is fresh
      refetchOnMount: false,
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      retryDelay: 1000,
    },
  },
});

/**
 * Query keys factory for consistent cache key management
 */
export const queryKeys = {
  // Authentication
  auth: {
    currentUser: ['auth', 'currentUser'] as const,
  },

  // Organizations
  organizations: {
    all: ['organizations'] as const,
    list: (filters?: Record<string, unknown>) => ['organizations', 'list', filters] as const,
    detail: (id: string) => ['organizations', 'detail', id] as const,
  },

  // Devices
  devices: {
    all: ['devices'] as const,
    list: (filters?: Record<string, unknown>) => ['devices', 'list', filters] as const,
    detail: (id: string) => ['devices', 'detail', id] as const,
    telemetry: (id: string, params?: Record<string, unknown>) =>
      ['devices', 'telemetry', id, params] as const,
  },

  // Experiments
  experiments: {
    all: ['experiments'] as const,
    list: (filters?: Record<string, unknown>) => ['experiments', 'list', filters] as const,
    detail: (id: string) => ['experiments', 'detail', id] as const,
    results: (id: string, filters?: Record<string, unknown>) =>
      ['experiments', 'results', id, filters] as const,
  },

  // Tasks
  tasks: {
    all: ['tasks'] as const,
    list: (filters?: Record<string, unknown>) => ['tasks', 'list', filters] as const,
    detail: (id: string) => ['tasks', 'detail', id] as const,
    templates: (filters?: Record<string, unknown>) => ['tasks', 'templates', filters] as const,
  },

  // Primates/Participants
  primates: {
    all: ['primates'] as const,
    list: (filters?: Record<string, unknown>) => ['primates', 'list', filters] as const,
    detail: (id: string) => ['primates', 'detail', id] as const,
    welfareChecks: (id: string) => ['primates', 'welfareChecks', id] as const,
    sessionHistory: (id: string) => ['primates', 'sessionHistory', id] as const,
  },
} as const;
