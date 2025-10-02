/**
 * WebSocket Provider
 * Manages WebSocket connection lifecycle and provides socket context
 */

'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { socketClient } from '@/lib/websocket';
import { useAuthStore } from '@/lib/stores';

interface SocketContextValue {
  isConnected: boolean;
}

const SocketContext = createContext<SocketContextValue>({
  isConnected: false,
});

export function useSocketContext() {
  return useContext(SocketContext);
}

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const { accessToken, isAuthenticated } = useAuthStore();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Only connect if authenticated
    if (!isAuthenticated || !accessToken) {
      socketClient.disconnect();
      setIsConnected(false);
      return;
    }

    // Connect to WebSocket
    socketClient.connect(accessToken);

    // Monitor connection status
    const checkConnection = setInterval(() => {
      setIsConnected(socketClient.isConnected());
    }, 1000);

    // Disconnect on unmount
    return () => {
      clearInterval(checkConnection);
      socketClient.disconnect();
      setIsConnected(false);
    };
  }, [isAuthenticated, accessToken]);

  return (
    <SocketContext.Provider value={{ isConnected }}>
      {children}
    </SocketContext.Provider>
  );
}
