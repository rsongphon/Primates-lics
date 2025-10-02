/**
 * WebSocket Client
 * Socket.IO client for real-time communication with backend
 */

import { io, Socket } from 'socket.io-client';
import type {
  WebSocketEventName,
  WebSocketEventPayload,
  WebSocketEvents,
} from '@/types/websocket';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001';

class SocketClient {
  private socket: Socket | null = null;
  private isConnecting: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  /**
   * Connect to WebSocket server with authentication
   */
  connect(token: string): Socket {
    if (this.socket?.connected) {
      return this.socket;
    }

    if (this.isConnecting) {
      return this.socket!;
    }

    this.isConnecting = true;

    this.socket = io(WS_URL, {
      auth: {
        token,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    });

    this.setupEventHandlers();
    this.isConnecting = false;

    return this.socket;
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.reconnectAttempts = 0;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * Subscribe to an event
   */
  on<T extends WebSocketEventName>(
    event: T,
    handler: (payload: WebSocketEventPayload<T>) => void
  ): void {
    if (!this.socket) {
      console.warn('Socket not connected. Call connect() first.');
      return;
    }

    this.socket.on(event, handler);
  }

  /**
   * Unsubscribe from an event
   */
  off<T extends WebSocketEventName>(
    event: T,
    handler?: (payload: WebSocketEventPayload<T>) => void
  ): void {
    if (!this.socket) {
      return;
    }

    if (handler) {
      this.socket.off(event, handler);
    } else {
      this.socket.off(event);
    }
  }

  /**
   * Emit an event to the server
   */
  emit<T extends WebSocketEventName>(
    event: T,
    payload: WebSocketEventPayload<T>
  ): void {
    if (!this.socket?.connected) {
      console.warn('Socket not connected. Cannot emit event:', event);
      return;
    }

    this.socket.emit(event, payload);
  }

  /**
   * Join a room (for room-based broadcasting)
   */
  joinRoom(room: string): void {
    if (!this.socket?.connected) {
      console.warn('Socket not connected. Cannot join room:', room);
      return;
    }

    this.socket.emit('join_room', { room });
  }

  /**
   * Leave a room
   */
  leaveRoom(room: string): void {
    if (!this.socket?.connected) {
      console.warn('Socket not connected. Cannot leave room:', room);
      return;
    }

    this.socket.emit('leave_room', { room });
  }

  /**
   * Subscribe to device updates
   */
  subscribeToDevice(deviceId: string): void {
    this.joinRoom(`device:${deviceId}`);
  }

  /**
   * Unsubscribe from device updates
   */
  unsubscribeFromDevice(deviceId: string): void {
    this.leaveRoom(`device:${deviceId}`);
  }

  /**
   * Subscribe to experiment updates
   */
  subscribeToExperiment(experimentId: string): void {
    this.joinRoom(`experiment:${experimentId}`);
  }

  /**
   * Unsubscribe from experiment updates
   */
  unsubscribeFromExperiment(experimentId: string): void {
    this.leaveRoom(`experiment:${experimentId}`);
  }

  /**
   * Subscribe to organization updates
   */
  subscribeToOrganization(orgId: string): void {
    this.joinRoom(`org:${orgId}`);
  }

  /**
   * Unsubscribe from organization updates
   */
  unsubscribeFromOrganization(orgId: string): void {
    this.leaveRoom(`org:${orgId}`);
  }

  /**
   * Setup internal event handlers for connection lifecycle
   */
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('❌ WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached. Giving up.');
        this.disconnect();
      }
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
      this.reconnectAttempts = 0;
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 Reconnection attempt ${attemptNumber}...`);
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('Reconnection error:', error);
    });

    this.socket.on('reconnect_failed', () => {
      console.error('❌ Reconnection failed after max attempts');
      this.disconnect();
    });

    // Heartbeat for connection health monitoring
    this.socket.on('ping', () => {
      this.socket?.emit('pong');
    });
  }

  /**
   * Get the underlying Socket.IO instance
   * (use sparingly, prefer typed methods above)
   */
  getSocket(): Socket | null {
    return this.socket;
  }
}

// Export singleton instance
export const socketClient = new SocketClient();

// Export class for testing purposes
export { SocketClient };
