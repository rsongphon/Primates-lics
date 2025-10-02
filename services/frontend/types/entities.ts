/**
 * Domain Entity Types
 * Type definitions for all domain entities matching backend schemas
 */

// ===== Base Types =====

export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

// ===== Organization Types =====

export interface Organization extends BaseEntity {
  name: string;
  description?: string;
  settings?: Record<string, unknown>;
  is_active: boolean;
}

// ===== User and Auth Types =====

export interface User extends BaseEntity {
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  organization_id: string;
  organization?: Organization;
  roles?: Role[];
}

export interface Role extends BaseEntity {
  name: string;
  description?: string;
  permissions?: Permission[];
}

export interface Permission extends BaseEntity {
  name: string;
  resource: string;
  action: string;
  description?: string;
}

// ===== Device Types =====

export enum DeviceType {
  RASPBERRY_PI = 'raspberry_pi',
  JETSON_NANO = 'jetson_nano',
  CUSTOM = 'custom',
}

export enum DeviceStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  BUSY = 'busy',
  ERROR = 'error',
  MAINTENANCE = 'maintenance',
}

export interface DeviceCapabilities {
  sensors?: string[];
  actuators?: string[];
  gpio_pins?: number;
  camera?: boolean;
  audio?: boolean;
  [key: string]: unknown;
}

export interface Device extends BaseEntity {
  name: string;
  device_type: DeviceType;
  organization_id: string;
  organization?: Organization;
  status: DeviceStatus;
  capabilities: DeviceCapabilities;
  hardware_config?: Record<string, unknown>;
  software_config?: Record<string, unknown>;
  last_seen?: string;
  ip_address?: string;
  mac_address?: string;
  location?: string;
  is_active: boolean;
}

export interface DeviceData {
  device_id: string;
  timestamp: string;
  metric: string;
  value: number;
  tags?: Record<string, unknown>;
}

// ===== Experiment Types =====

export enum ExperimentState {
  DRAFT = 'draft',
  SCHEDULED = 'scheduled',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed',
}

export interface Experiment extends BaseEntity {
  name: string;
  description?: string;
  organization_id: string;
  organization?: Organization;
  task_id: string;
  task?: Task;
  device_id?: string;
  device?: Device;
  state: ExperimentState;
  scheduled_start?: string;
  scheduled_end?: string;
  actual_start?: string;
  actual_end?: string;
  experiment_metadata?: Record<string, unknown>;
  results_summary?: Record<string, unknown>;
}

export interface ExperimentData extends BaseEntity {
  experiment_id: string;
  experiment?: Experiment;
  participant_id?: string;
  participant?: Primate;
  trial_number?: number;
  timestamp: string;
  data_type: string;
  data_content: Record<string, unknown>;
  data_metadata?: Record<string, unknown>;
}

// ===== Participant (Primate) Types =====

export enum PrimateSpecies {
  MACAQUE = 'macaque',
  MARMOSET = 'marmoset',
  CAPUCHIN = 'capuchin',
  RHESUS = 'rhesus',
  OTHER = 'other',
}

export enum Sex {
  MALE = 'M',
  FEMALE = 'F',
  UNKNOWN = 'U',
}

export enum HealthStatus {
  EXCELLENT = 'excellent',
  GOOD = 'good',
  FAIR = 'fair',
  CONCERN = 'concern',
}

export interface Primate extends BaseEntity {
  name: string;
  organization_id: string;
  organization?: Organization;
  species: PrimateSpecies;
  rfid_tag?: string;
  birth_date?: string;
  sex: Sex;
  weight_kg?: number;
  training_level: number;
  is_active: boolean;
  current_device_id?: string;
  current_device?: Device;
  current_experiment_id?: string;
  current_experiment?: Experiment;
  notes?: string;
  participant_metadata?: Record<string, unknown>;
}

export interface WelfareCheck {
  id: string;
  primate_id: string;
  check_date: string;
  weight_kg?: number;
  behavioral_observations?: string;
  health_status: HealthStatus;
  veterinary_notes?: string;
  created_at: string;
  created_by?: string;
}

export interface ExperimentSession {
  id: string;
  experiment_id: string;
  primate_id: string;
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  trial_count?: number;
  success_rate?: number;
}

// ===== Task Types =====

export enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export interface TaskDefinition {
  version: string;
  nodes: TaskNode[];
  edges: TaskEdge[];
  variables?: Record<string, unknown>;
}

export interface TaskNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface TaskEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface Task extends BaseEntity {
  name: string;
  description?: string;
  organization_id: string;
  organization?: Organization;
  task_definition: TaskDefinition;
  is_template: boolean;
  is_published: boolean;
  version: string;
  tags?: string[];
  required_hardware?: string[];
  minimum_training_level?: number;
}

export interface TaskExecution extends BaseEntity {
  task_id: string;
  task?: Task;
  experiment_id?: string;
  experiment?: Experiment;
  device_id?: string;
  device?: Device;
  status: ExecutionStatus;
  started_at?: string;
  completed_at?: string;
  result?: Record<string, unknown>;
  error_message?: string;
}

// ===== Notification Types =====

export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error',
}

export interface Notification {
  id: string;
  type: NotificationType;
  title?: string;
  message: string;
  timestamp: string;
  read?: boolean;
  action?: {
    label: string;
    url: string;
  };
}
