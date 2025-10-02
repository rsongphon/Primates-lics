/**
 * usePagination Hook
 * Manage pagination state for lists and tables
 */

import { useState, useCallback, useMemo } from 'react';

export interface PaginationState {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface PaginationActions {
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
  setTotalItems: (total: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  goToFirstPage: () => void;
  goToLastPage: () => void;
  canGoNext: boolean;
  canGoPrevious: boolean;
}

export interface UsePaginationReturn extends PaginationState, PaginationActions {}

/**
 * Hook for managing pagination state
 */
export function usePagination(
  initialPage: number = 1,
  initialPageSize: number = 10,
  initialTotalItems: number = 0
): UsePaginationReturn {
  const [page, setPageState] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);
  const [totalItems, setTotalItems] = useState(initialTotalItems);

  // Calculate total pages
  const totalPages = useMemo(() => {
    return Math.ceil(totalItems / pageSize) || 1;
  }, [totalItems, pageSize]);

  // Set page with bounds checking
  const setPage = useCallback(
    (newPage: number) => {
      const boundedPage = Math.max(1, Math.min(newPage, totalPages));
      setPageState(boundedPage);
    },
    [totalPages]
  );

  // Set page size and reset to first page
  const setPageSize = useCallback((newPageSize: number) => {
    setPageSizeState(newPageSize);
    setPageState(1); // Reset to first page when page size changes
  }, []);

  // Navigate to next page
  const nextPage = useCallback(() => {
    setPage(page + 1);
  }, [page, setPage]);

  // Navigate to previous page
  const previousPage = useCallback(() => {
    setPage(page - 1);
  }, [page, setPage]);

  // Go to first page
  const goToFirstPage = useCallback(() => {
    setPage(1);
  }, [setPage]);

  // Go to last page
  const goToLastPage = useCallback(() => {
    setPage(totalPages);
  }, [setPage, totalPages]);

  // Check if can navigate
  const canGoNext = page < totalPages;
  const canGoPrevious = page > 1;

  return {
    page,
    pageSize,
    totalItems,
    totalPages,
    setPage,
    setPageSize,
    setTotalItems,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    canGoNext,
    canGoPrevious,
  };
}
