import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface LoadingProps {
  variant?: 'spinner' | 'skeleton' | 'progress';
  text?: string;
  className?: string;
}

export function Loading({ variant = 'spinner', text, className }: LoadingProps) {
  if (variant === 'skeleton') {
    return (
      <div className={cn('space-y-4', className)}>
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </div>
    );
  }

  if (variant === 'progress') {
    return (
      <div className={cn('space-y-4', className)}>
        <div className="overflow-hidden rounded-full bg-secondary">
          <div
            className="h-2 animate-pulse bg-primary transition-all duration-300"
            style={{ width: '60%' }}
          />
        </div>
        {text && <p className="text-center text-sm text-muted-foreground">{text}</p>}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col items-center justify-center space-y-4', className)}>
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
      {text && <p className="text-sm text-muted-foreground">{text}</p>}
    </div>
  );
}

// Page Loading Component
export function PageLoading() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <Loading text="Loading..." />
    </div>
  );
}

// Card Loading Skeleton
export function CardLoading() {
  return (
    <div className="space-y-4 rounded-lg border p-6">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
      <div className="flex space-x-2 pt-4">
        <Skeleton className="h-9 w-20" />
        <Skeleton className="h-9 w-20" />
      </div>
    </div>
  );
}

// Table Loading Skeleton
export function TableLoading({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex space-x-4">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-8 w-1/4" />
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4">
          <Skeleton className="h-6 w-1/4" />
          <Skeleton className="h-6 w-1/4" />
          <Skeleton className="h-6 w-1/4" />
          <Skeleton className="h-6 w-1/4" />
        </div>
      ))}
    </div>
  );
}

// Inline Spinner
export function InlineSpinner({ className }: { className?: string }) {
  return (
    <div className={cn('inline-block h-4 w-4', className)}>
      <div className="h-full w-full animate-spin rounded-full border-2 border-current border-t-transparent" />
    </div>
  );
}
