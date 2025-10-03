// Testing Utilities
// Provides custom render functions and test helpers

import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create a custom render function with providers
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Disable retries in tests
        gcTime: 0, // Disable cache in tests
      },
    },
  })
}

interface AllTheProvidersProps {
  children: React.ReactNode
}

export function AllTheProviders({ children }: AllTheProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options })

export * from '@testing-library/react'
export { customRender as render }

// Mock data generators
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  organization_id: 'org-123',
  roles: [
    {
      id: 'role-123',
      name: 'researcher',
      permissions: [
        { id: 'perm-1', name: 'read:devices', resource: 'devices', action: 'read' },
        { id: 'perm-2', name: 'write:experiments', resource: 'experiments', action: 'write' },
      ],
    },
  ],
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

export const mockTokens = {
  access_token: 'mock-access-token-123',
  refresh_token: 'mock-refresh-token-456',
  token_type: 'bearer',
}

export const mockDevice = {
  id: 'device-123',
  name: 'Test Device',
  device_type: 'raspberry_pi',
  status: 'online' as const,
  organization_id: 'org-123',
  capabilities: {
    sensors: ['temperature', 'humidity'],
    actuators: ['led', 'buzzer'],
  },
  last_seen: '2024-01-01T12:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
}

export const mockExperiment = {
  id: 'exp-123',
  name: 'Test Experiment',
  description: 'A test experiment',
  state: 'draft' as const,
  organization_id: 'org-123',
  task_id: 'task-123',
  device_id: 'device-123',
  created_by: 'user-123',
  created_at: '2024-01-01T00:00:00Z',
}

export const mockPrimate = {
  id: 'primate-123',
  name: 'Monkey-42',
  species: 'macaque' as const,
  rfid_tag: 'RFID-12345',
  organization_id: 'org-123',
  training_level: 3,
  is_active: true,
  birth_date: '2020-01-01',
  sex: 'M' as const,
  weight_kg: 8.5,
  created_at: '2024-01-01T00:00:00Z',
}

// Helper to wait for async updates
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0))

// Helper to mock fetch responses
export function mockFetch(data: any, ok = true) {
  return jest.fn().mockImplementation(() =>
    Promise.resolve({
      ok,
      json: () => Promise.resolve(data),
      status: ok ? 200 : 400,
    })
  )
}

// Helper to mock axios responses
export function mockAxiosResponse(data: any, status = 200) {
  return Promise.resolve({
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as any,
  })
}

// Helper to mock axios error
export function mockAxiosError(message: string, status = 400) {
  return Promise.reject({
    response: {
      data: { error: { message } },
      status,
      statusText: 'Bad Request',
    },
    message,
  })
}
