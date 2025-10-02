/**
 * useSocketEvent Hook
 * React hook for subscribing to specific WebSocket events
 */

import { useEffect, useRef } from 'react';
import { useSocket } from './use-socket';
import type { WebSocketEventName, WebSocketEventPayload } from '@/types/websocket';

/**
 * Hook for subscribing to a specific WebSocket event
 * Automatically subscribes on mount and unsubscribes on unmount
 */
export function useSocketEvent<T extends WebSocketEventName>(
  event: T,
  handler: (payload: WebSocketEventPayload<T>) => void,
  deps: React.DependencyList = []
) {
  const { on, off, isConnected } = useSocket({ autoConnect: true });
  const handlerRef = useRef(handler);

  // Update handler ref when it changes
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  // Subscribe to event when connected
  useEffect(() => {
    if (!isConnected) return;

    const eventHandler = (payload: WebSocketEventPayload<T>) => {
      handlerRef.current(payload);
    };

    on(event, eventHandler);

    return () => {
      off(event, eventHandler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected, event, ...deps]);
}

/**
 * Hook for subscribing to device events
 */
export function useDeviceEvents(deviceId: string) {
  const { subscribeToDevice, unsubscribeFromDevice, isConnected } = useSocket({ autoConnect: true });

  useEffect(() => {
    if (!isConnected || !deviceId) return;

    subscribeToDevice(deviceId);

    return () => {
      unsubscribeFromDevice(deviceId);
    };
  }, [deviceId, isConnected, subscribeToDevice, unsubscribeFromDevice]);
}

/**
 * Hook for subscribing to experiment events
 */
export function useExperimentEvents(experimentId: string) {
  const { subscribeToExperiment, unsubscribeFromExperiment, isConnected } = useSocket({ autoConnect: true });

  useEffect(() => {
    if (!isConnected || !experimentId) return;

    subscribeToExperiment(experimentId);

    return () => {
      unsubscribeFromExperiment(experimentId);
    };
  }, [experimentId, isConnected, subscribeToExperiment, unsubscribeFromExperiment]);
}

/**
 * Hook for subscribing to organization events
 */
export function useOrganizationEvents(orgId: string) {
  const { subscribeToOrganization, unsubscribeFromOrganization, isConnected } = useSocket({ autoConnect: true });

  useEffect(() => {
    if (!isConnected || !orgId) return;

    subscribeToOrganization(orgId);

    return () => {
      unsubscribeFromOrganization(orgId);
    };
  }, [orgId, isConnected, subscribeToOrganization, unsubscribeFromOrganization]);
}
