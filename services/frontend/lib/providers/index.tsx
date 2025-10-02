/**
 * Providers Index
 * Central component that wraps the app with all necessary providers
 */

'use client';

import { QueryProvider } from './query-provider';
import { SocketProvider } from './socket-provider';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <SocketProvider>
        {children}
      </SocketProvider>
    </QueryProvider>
  );
}

// Re-export individual providers
export { QueryProvider } from './query-provider';
export { SocketProvider, useSocketContext } from './socket-provider';
