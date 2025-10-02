/**
 * Devices API
 * API functions for device management and telemetry
 */

import apiClient, { unwrapApiResponse } from './client';
import type { ApiResponse, PaginatedResponse, Device, DeviceData, QueryParams } from '@/types';

export interface DeviceFilters extends QueryParams {
  status?: string;
  device_type?: string;
  organization_id?: string;
}

export interface DeviceCreateData {
  name: string;
  device_type: string;
  capabilities?: Record<string, unknown>;
  hardware_config?: Record<string, unknown>;
  software_config?: Record<string, unknown>;
  location?: string;
}

export interface DeviceUpdateData extends Partial<DeviceCreateData> {
  status?: string;
  is_active?: boolean;
}

/**
 * Get list of devices
 */
export async function getDevices(filters?: DeviceFilters): Promise<PaginatedResponse<Device>> {
  const response = await apiClient.get<PaginatedResponse<Device>>('/devices', { params: filters });
  return response.data;
}

/**
 * Get single device by ID
 */
export async function getDevice(id: string): Promise<Device> {
  const response = await apiClient.get<ApiResponse<Device>>(`/devices/${id}`);
  return unwrapApiResponse(response.data);
}

/**
 * Create new device
 */
export async function createDevice(data: DeviceCreateData): Promise<Device> {
  const response = await apiClient.post<ApiResponse<Device>>('/devices', data);
  return unwrapApiResponse(response.data);
}

/**
 * Update device
 */
export async function updateDevice(id: string, data: DeviceUpdateData): Promise<Device> {
  const response = await apiClient.patch<ApiResponse<Device>>(`/devices/${id}`, data);
  return unwrapApiResponse(response.data);
}

/**
 * Delete device
 */
export async function deleteDevice(id: string): Promise<void> {
  await apiClient.delete(`/devices/${id}`);
}

/**
 * Send heartbeat for device
 */
export async function sendHeartbeat(id: string, systemInfo?: Record<string, unknown>): Promise<void> {
  await apiClient.post(`/devices/${id}/heartbeat`, { system_info: systemInfo });
}

/**
 * Update device status
 */
export async function updateDeviceStatus(id: string, status: string): Promise<void> {
  await apiClient.post(`/devices/${id}/status`, { status });
}

/**
 * Get device telemetry data
 */
export async function getDeviceTelemetry(
  id: string,
  params?: { metric?: string; start_time?: string; end_time?: string }
): Promise<DeviceData[]> {
  const response = await apiClient.get<ApiResponse<DeviceData[]>>(`/devices/${id}/telemetry`, {
    params,
  });
  return unwrapApiResponse(response.data);
}

/**
 * Post device telemetry data
 */
export async function postDeviceTelemetry(id: string, data: Omit<DeviceData, 'device_id'>): Promise<void> {
  await apiClient.post(`/devices/${id}/telemetry`, data);
}

export const devicesApi = {
  getDevices,
  getDevice,
  createDevice,
  updateDevice,
  deleteDevice,
  sendHeartbeat,
  updateDeviceStatus,
  getDeviceTelemetry,
  postDeviceTelemetry,
};
