/**
 * WebSocket Index
 * Central export point for WebSocket client and hooks
 */

export { socketClient, SocketClient } from './socket-client';
export { useSocket } from './use-socket';
export {
  useSocketEvent,
  useDeviceEvents,
  useExperimentEvents,
  useOrganizationEvents,
} from './use-socket-event';

export type { UseSocketOptions } from './use-socket';
