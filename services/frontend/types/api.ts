/**
 * API Types and Interfaces
 * Type definitions for API requests and responses
 */

export interface ApiResponse<T> {
  data: T;
  meta?: {
    timestamp: string;
    version: string;
  };
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  links?: {
    first?: string;
    last?: string;
    prev?: string;
    next?: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    trace_id?: string;
  };
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface FilterParams {
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export type QueryParams = PaginationParams & FilterParams;
