'use client';

import { Component, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // Call optional error handler
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="flex min-h-[400px] items-center justify-center p-6">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <div className="flex items-center space-x-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="text-destructive"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" x2="12" y1="8" y2="12" />
                  <line x1="12" x2="12.01" y1="16" y2="16" />
                </svg>
                <CardTitle>Something went wrong</CardTitle>
              </div>
              <CardDescription>
                An unexpected error occurred. Please try again or contact support if the problem
                persists.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-sm font-medium">Error details:</p>
                <div className="rounded-md bg-muted p-3">
                  <code className="text-xs text-muted-foreground">
                    {this.state.error?.message || 'Unknown error'}
                  </code>
                </div>
                {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
                  <details className="cursor-pointer">
                    <summary className="text-sm font-medium text-muted-foreground hover:text-foreground">
                      Stack trace (development only)
                    </summary>
                    <pre className="mt-2 overflow-auto rounded-md bg-muted p-3 text-xs">
                      <code>{this.state.errorInfo.componentStack}</code>
                    </pre>
                  </details>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex space-x-2">
              <Button onClick={this.handleReset}>Try Again</Button>
              <Button variant="outline" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
              <Button variant="ghost" onClick={() => (window.location.href = '/')}>
                Go Home
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Simplified Error Display Component
interface ErrorDisplayProps {
  error?: Error | string;
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorDisplay({
  error,
  title = 'Error',
  description = 'An error occurred while loading this content.',
  onRetry,
  className,
}: ErrorDisplayProps) {
  const errorMessage = typeof error === 'string' ? error : error?.message;

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center space-x-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-destructive"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <line x1="12" x2="12.01" y1="16" y2="16" />
          </svg>
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {errorMessage && (
        <CardContent>
          <div className="rounded-md bg-muted p-3">
            <code className="text-xs text-muted-foreground">{errorMessage}</code>
          </div>
        </CardContent>
      )}
      {onRetry && (
        <CardFooter>
          <Button onClick={onRetry} size="sm">
            Retry
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
