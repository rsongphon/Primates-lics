/**
 * WebSocket Event Types
 * Type definitions for WebSocket events and payloads
 */

import type {
  Device,
  DeviceStatus,
  Experiment,
  ExperimentState,
  Primate,
  TaskExecution,
  ExecutionStatus,
} from './entities';

// ===== WebSocket Event Payloads =====

export interface DeviceStatusEvent {
  device_id: string;
  status: DeviceStatus;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface DeviceTelemetryEvent {
  device_id: string;
  metric: string;
  value: number;
  timestamp: string;
  tags?: Record<string, unknown>;
}

export interface DeviceHeartbeatEvent {
  device_id: string;
  timestamp: string;
  system_info?: Record<string, unknown>;
}

export interface ExperimentStateChangeEvent {
  experiment_id: string;
  old_state: ExperimentState;
  new_state: ExperimentState;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ExperimentProgressEvent {
  experiment_id: string;
  progress: number; // 0-100
  current_trial?: number;
  total_trials?: number;
  success_rate?: number;
  timestamp: string;
}

export interface ExperimentDataCollectedEvent {
  experiment_id: string;
  trial_number: number;
  data_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface TaskExecutionStartedEvent {
  task_execution_id: string;
  task_id: string;
  device_id: string;
  timestamp: string;
}

export interface TaskExecutionProgressEvent {
  task_execution_id: string;
  progress: number;
  current_step?: string;
  timestamp: string;
}

export interface TaskExecutionCompletedEvent {
  task_execution_id: string;
  status: ExecutionStatus;
  result?: Record<string, unknown>;
  error_message?: string;
  timestamp: string;
}

export interface PrimateDetectedEvent {
  primate_id: string;
  primate_name: string;
  rfid_tag: string;
  device_id: string;
  device_name: string;
  timestamp: string;
}

export interface NotificationEvent {
  notification_id: string;
  type: 'system' | 'user' | 'alert';
  title?: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface UserPresenceEvent {
  user_id: string;
  status: 'online' | 'offline' | 'away';
  timestamp: string;
}

// ===== WebSocket Event Map =====

export interface WebSocketEvents {
  // Device events
  'device:status': DeviceStatusEvent;
  'device:telemetry': DeviceTelemetryEvent;
  'device:heartbeat': DeviceHeartbeatEvent;

  // Experiment events
  'experiment:state_change': ExperimentStateChangeEvent;
  'experiment:progress': ExperimentProgressEvent;
  'experiment:data_collected': ExperimentDataCollectedEvent;

  // Task events
  'task:execution_started': TaskExecutionStartedEvent;
  'task:execution_progress': TaskExecutionProgressEvent;
  'task:execution_completed': TaskExecutionCompletedEvent;

  // Primate events
  'primate:detected': PrimateDetectedEvent;

  // Notification events
  'notification:system': NotificationEvent;
  'notification:user': NotificationEvent;
  'notification:alert': NotificationEvent;

  // Presence events
  'user:presence': UserPresenceEvent;

  // Connection events
  connect: void;
  disconnect: void;
  reconnect: void;
  error: Error;
}

export type WebSocketEventName = keyof WebSocketEvents;

export type WebSocketEventPayload<T extends WebSocketEventName> = WebSocketEvents[T];

// ===== Room Names =====

export const getRoomName = {
  device: (deviceId: string) => `device:${deviceId}`,
  experiment: (experimentId: string) => `experiment:${experimentId}`,
  task: (taskId: string) => `task:${taskId}`,
  user: (userId: string) => `user:${userId}`,
  organization: (orgId: string) => `organization:${orgId}`,
};
