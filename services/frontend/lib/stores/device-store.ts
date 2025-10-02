/**
 * Device Store
 * Device management and real-time status tracking
 */

import { create } from 'zustand';
import type { Device, DeviceStatus } from '@/types';

interface DeviceState {
  // Devices
  devices: Device[];
  selectedDevice: Device | null;
  setDevices: (devices: Device[]) => void;
  addDevice: (device: Device) => void;
  updateDevice: (id: string, updates: Partial<Device>) => void;
  removeDevice: (id: string) => void;
  setSelectedDevice: (device: Device | null) => void;
  getDevice: (id: string) => Device | undefined;

  // Real-time status tracking
  deviceStatus: Map<string, DeviceStatus>;
  updateDeviceStatus: (deviceId: string, status: DeviceStatus) => void;
  getDeviceStatus: (deviceId: string) => DeviceStatus | undefined;

  // Loading and error states
  isLoading: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Utility
  clearDevices: () => void;
  getOnlineDevices: () => Device[];
  getDevicesByOrganization: (orgId: string) => Device[];
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  // Initial state
  devices: [],
  selectedDevice: null,
  deviceStatus: new Map(),
  isLoading: false,
  error: null,

  // Device management
  setDevices: (devices) => set({ devices }),

  addDevice: (device) =>
    set((state) => ({
      devices: [...state.devices, device],
    })),

  updateDevice: (id, updates) =>
    set((state) => ({
      devices: state.devices.map((d) => (d.id === id ? { ...d, ...updates } : d)),
      selectedDevice:
        state.selectedDevice?.id === id
          ? { ...state.selectedDevice, ...updates }
          : state.selectedDevice,
    })),

  removeDevice: (id) =>
    set((state) => ({
      devices: state.devices.filter((d) => d.id !== id),
      selectedDevice: state.selectedDevice?.id === id ? null : state.selectedDevice,
    })),

  setSelectedDevice: (device) => set({ selectedDevice: device }),

  getDevice: (id) => get().devices.find((d) => d.id === id),

  // Real-time status
  updateDeviceStatus: (deviceId, status) =>
    set((state) => {
      const newStatusMap = new Map(state.deviceStatus);
      newStatusMap.set(deviceId, status);

      // Also update device in devices array
      const devices = state.devices.map((d) =>
        d.id === deviceId ? { ...d, status, last_seen: new Date().toISOString() } : d
      );

      return {
        deviceStatus: newStatusMap,
        devices,
      };
    }),

  getDeviceStatus: (deviceId) => get().deviceStatus.get(deviceId),

  // Loading and error
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Utility methods
  clearDevices: () =>
    set({
      devices: [],
      selectedDevice: null,
      deviceStatus: new Map(),
    }),

  getOnlineDevices: () => get().devices.filter((d) => d.status === 'online'),

  getDevicesByOrganization: (orgId) =>
    get().devices.filter((d) => d.organization_id === orgId),
}));
