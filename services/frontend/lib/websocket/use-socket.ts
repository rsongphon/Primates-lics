/**
 * useSocket Hook
 * React hook for WebSocket functionality
 */

import { useEffect, useCallback, useState } from 'react';
import { socketClient } from './socket-client';
import { useAuthStore } from '@/lib/stores';
import type { WebSocketEventName, WebSocketEventPayload } from '@/types/websocket';

export interface UseSocketOptions {
  /**
   * Auto-connect when hook mounts
   * Default: true
   */
  autoConnect?: boolean;

  /**
   * Auto-disconnect when hook unmounts
   * Default: true
   */
  autoDisconnect?: boolean;

  /**
   * Rooms to automatically join on connect
   */
  autoJoinRooms?: string[];
}

/**
 * Hook for WebSocket functionality
 */
export function useSocket(options: UseSocketOptions = {}) {
  const {
    autoConnect = true,
    autoDisconnect = true,
    autoJoinRooms = [],
  } = options;

  const { accessToken, isAuthenticated } = useAuthStore();
  const [isConnected, setIsConnected] = useState(false);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!accessToken) {
      console.warn('Cannot connect to WebSocket: no access token');
      return;
    }

    socketClient.connect(accessToken);
    setIsConnected(socketClient.isConnected());
  }, [accessToken]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    socketClient.disconnect();
    setIsConnected(false);
  }, []);

  // Subscribe to an event
  const on = useCallback(
    <T extends WebSocketEventName>(
      event: T,
      handler: (payload: WebSocketEventPayload<T>) => void
    ) => {
      socketClient.on(event, handler);
    },
    []
  );

  // Unsubscribe from an event
  const off = useCallback(
    <T extends WebSocketEventName>(
      event: T,
      handler?: (payload: WebSocketEventPayload<T>) => void
    ) => {
      socketClient.off(event, handler);
    },
    []
  );

  // Emit an event
  const emit = useCallback(
    <T extends WebSocketEventName>(
      event: T,
      payload: WebSocketEventPayload<T>
    ) => {
      socketClient.emit(event, payload);
    },
    []
  );

  // Join a room
  const joinRoom = useCallback((room: string) => {
    socketClient.joinRoom(room);
  }, []);

  // Leave a room
  const leaveRoom = useCallback((room: string) => {
    socketClient.leaveRoom(room);
  }, []);

  // Subscribe to device updates
  const subscribeToDevice = useCallback((deviceId: string) => {
    socketClient.subscribeToDevice(deviceId);
  }, []);

  // Unsubscribe from device updates
  const unsubscribeFromDevice = useCallback((deviceId: string) => {
    socketClient.unsubscribeFromDevice(deviceId);
  }, []);

  // Subscribe to experiment updates
  const subscribeToExperiment = useCallback((experimentId: string) => {
    socketClient.subscribeToExperiment(experimentId);
  }, []);

  // Unsubscribe from experiment updates
  const unsubscribeFromExperiment = useCallback((experimentId: string) => {
    socketClient.unsubscribeFromExperiment(experimentId);
  }, []);

  // Subscribe to organization updates
  const subscribeToOrganization = useCallback((orgId: string) => {
    socketClient.subscribeToOrganization(orgId);
  }, []);

  // Unsubscribe from organization updates
  const unsubscribeFromOrganization = useCallback((orgId: string) => {
    socketClient.unsubscribeFromOrganization(orgId);
  }, []);

  // Auto-connect on mount if authenticated
  useEffect(() => {
    if (autoConnect && isAuthenticated && accessToken) {
      connect();

      // Monitor connection status
      const checkConnection = setInterval(() => {
        setIsConnected(socketClient.isConnected());
      }, 1000);

      return () => {
        clearInterval(checkConnection);
        if (autoDisconnect) {
          disconnect();
        }
      };
    }
  }, [autoConnect, autoDisconnect, isAuthenticated, accessToken, connect, disconnect]);

  // Auto-join rooms on connect
  useEffect(() => {
    if (isConnected && autoJoinRooms.length > 0) {
      autoJoinRooms.forEach((room) => {
        joinRoom(room);
      });
    }
  }, [isConnected, autoJoinRooms, joinRoom]);

  return {
    isConnected,
    connect,
    disconnect,
    on,
    off,
    emit,
    joinRoom,
    leaveRoom,
    subscribeToDevice,
    unsubscribeFromDevice,
    subscribeToExperiment,
    unsubscribeFromExperiment,
    subscribeToOrganization,
    unsubscribeFromOrganization,
  };
}
