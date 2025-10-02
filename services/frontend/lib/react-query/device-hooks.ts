/**
 * Device React Query Hooks
 * Query and mutation hooks for device management operations
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  devicesApi,
  type DeviceFilters,
  type DeviceCreateData,
  type DeviceUpdateData,
} from '@/lib/api/devices';
import { useDeviceStore } from '@/lib/stores';
import { queryKeys } from './query-client';
import type { Device, DeviceData } from '@/types';

/**
 * Query: Get list of devices with filters
 */
export function useDevices(filters?: DeviceFilters) {
  return useQuery({
    queryKey: queryKeys.devices.list(filters),
    queryFn: () => devicesApi.getDevices(filters),
    staleTime: 30 * 1000, // 30 seconds - devices change frequently
  });
}

/**
 * Query: Get single device by ID
 */
export function useDevice(id: string) {
  return useQuery({
    queryKey: queryKeys.devices.detail(id),
    queryFn: () => devicesApi.getDevice(id),
    enabled: !!id, // Only fetch if ID is provided
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Query: Get device telemetry data
 */
export function useDeviceTelemetry(
  id: string,
  params?: { metric?: string; start_time?: string; end_time?: string }
) {
  return useQuery({
    queryKey: queryKeys.devices.telemetry(id, params),
    queryFn: () => devicesApi.getDeviceTelemetry(id, params),
    enabled: !!id,
    staleTime: 10 * 1000, // 10 seconds - telemetry is real-time
    refetchInterval: 5000, // Auto-refetch every 5 seconds
  });
}

/**
 * Mutation: Create device
 */
export function useCreateDevice() {
  const queryClient = useQueryClient();
  const { addDevice } = useDeviceStore();

  return useMutation({
    mutationFn: (data: DeviceCreateData) => devicesApi.createDevice(data),
    onSuccess: (newDevice) => {
      // Invalidate device list queries
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });

      // Add to store
      addDevice(newDevice);
    },
  });
}

/**
 * Mutation: Update device
 */
export function useUpdateDevice() {
  const queryClient = useQueryClient();
  const { updateDevice: updateDeviceStore } = useDeviceStore();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DeviceUpdateData }) =>
      devicesApi.updateDevice(id, data),
    onSuccess: (updatedDevice, { id }) => {
      // Update specific device query cache
      queryClient.setQueryData(queryKeys.devices.detail(id), updatedDevice);

      // Invalidate device list queries
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });

      // Update store
      updateDeviceStore(id, updatedDevice);
    },
  });
}

/**
 * Mutation: Delete device
 */
export function useDeleteDevice() {
  const queryClient = useQueryClient();
  const { removeDevice } = useDeviceStore();

  return useMutation({
    mutationFn: (id: string) => devicesApi.deleteDevice(id),
    onSuccess: (_, id) => {
      // Remove from device list cache
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });

      // Remove specific device cache
      queryClient.removeQueries({ queryKey: queryKeys.devices.detail(id) });

      // Remove from store
      removeDevice(id);
    },
  });
}

/**
 * Mutation: Send device heartbeat
 */
export function useSendHeartbeat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, systemInfo }: { id: string; systemInfo?: Record<string, unknown> }) =>
      devicesApi.sendHeartbeat(id, systemInfo),
    onSuccess: (_, { id }) => {
      // Invalidate device detail to refresh last_seen timestamp
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.detail(id) });
    },
  });
}

/**
 * Mutation: Update device status
 */
export function useUpdateDeviceStatus() {
  const queryClient = useQueryClient();
  const { updateDeviceStatus: updateStatusStore } = useDeviceStore();

  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      devicesApi.updateDeviceStatus(id, status),
    onSuccess: (_, { id, status }) => {
      // Optimistically update device cache
      queryClient.setQueryData<Device>(queryKeys.devices.detail(id), (oldData) => {
        if (!oldData) return oldData;
        return { ...oldData, status, last_seen: new Date().toISOString() };
      });

      // Invalidate device list
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.all });

      // Update store
      updateStatusStore(id, status as any);
    },
  });
}

/**
 * Mutation: Post device telemetry
 */
export function usePostDeviceTelemetry() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Omit<DeviceData, 'device_id'> }) =>
      devicesApi.postDeviceTelemetry(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate telemetry queries to show new data
      queryClient.invalidateQueries({ queryKey: queryKeys.devices.telemetry(id) });
    },
  });
}
