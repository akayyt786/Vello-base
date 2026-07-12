import type { OwnFirebaseConfig } from './types';

export interface RealtimeListenerOptions {
  path: string;
  query?: Record<string, unknown>;
}

export interface RealtimeChange {
  subscriptionId: string;
  event: 'added' | 'modified' | 'removed';
  data: Record<string, unknown>;
  version?: number;
}

export interface RealtimeSnapshot {
  subscriptionId: string;
  data: Record<string, unknown>;
  version: number;
}

export type ChangeListener = (change: RealtimeChange) => void;
export type SnapshotListener = (snapshot: RealtimeSnapshot) => void;
export type ErrorListener = (error: Error) => void;

export class RealtimeSDK {
  private baseUrl: string;
  private projectId: string | undefined;
  private accessToken: string | undefined;
  private ws: WebSocket | null = null;
  private subscriptions = new Map<string, {
    listeners: ChangeListener[];
    snapshotListeners: SnapshotListener[];
    errorListeners: ErrorListener[];
  }>();
  private requestId = 0;
  private pendingRequests = new Map<string, {
    resolve: (value: any) => void;
    reject: (reason?: any) => void;
    timeout: NodeJS.Timeout;
  }>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private isConnecting = false;

  constructor(config: OwnFirebaseConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '').replace(/^http/, 'ws');
    this.projectId = config.projectId;
    this.accessToken = config.accessToken;
  }

  setAccessToken(token: string): void {
    this.accessToken = token;
  }

  setProjectId(id: string): void {
    this.projectId = id;
  }

  /**
   * Connect to realtime WebSocket. Automatically reconnects on disconnect.
   */
  async connect(): Promise<void> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.baseUrl}/ws/v1/projects/${this.projectId}/listen/`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => this.handleMessage(event.data);

        this.ws.onerror = (event) => {
          this.isConnecting = false;
          reject(new Error(`WebSocket error: ${event}`));
        };

        this.ws.onclose = () => {
          this.isConnecting = false;
          this.attemptReconnect();
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from realtime WebSocket.
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    // Clear pending requests
    for (const { timeout } of this.pendingRequests.values()) {
      clearTimeout(timeout);
    }
    this.pendingRequests.clear();
  }

  /**
   * Subscribe to changes on a collection or document path.
   * @example
   * ```ts
   * const unsub = realtime.onSnapshot(
   *   { path: 'users' },
   *   (change) => console.log('Change:', change),
   *   (error) => console.error('Error:', error)
   * );
   * // Later: unsub();
   * ```
   */
  onSnapshot(
    options: RealtimeListenerOptions,
    onNext?: SnapshotListener,
    onError?: ErrorListener
  ): () => void {
    const listener = {
      listeners: [],
      snapshotListeners: onNext ? [onNext] : [],
      errorListeners: onError ? [onError] : [],
    };

    const subscribe = async () => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        await this.connect();
      }

      const requestId = String(++this.requestId);
      const subscriptionPromise = this.createPendingRequest(requestId);

      this.ws!.send(JSON.stringify({
        type: 'subscribe',
        requestId,
        path: options.path,
        query: options.query,
      }));

      try {
        const response = await subscriptionPromise;
        const subId = response.subscriptionId;

        if (!this.subscriptions.has(subId)) {
          this.subscriptions.set(subId, listener);
        } else {
          const existing = this.subscriptions.get(subId)!;
          existing.snapshotListeners.push(...listener.snapshotListeners);
          existing.errorListeners.push(...listener.errorListeners);
        }

        // Emit initial snapshot
        if (onNext && response.snapshot) {
          onNext({
            subscriptionId: subId,
            data: response.snapshot,
            version: response.version,
          });
        }

        return subId;
      } catch (error) {
        if (onError) {
          onError(error instanceof Error ? error : new Error(String(error)));
        }
        throw error;
      }
    };

    let subId: string | null = null;
    subscribe().then(id => { subId = id; }).catch(err => {
      if (onError) onError(err);
    });

    // Return unsubscribe function
    return () => {
      if (subId) {
        this.unsubscribe(subId);
      }
    };
  }

  /**
   * Listen to changes on a subscription (after onSnapshot).
   */
  onChange(
    subscriptionId: string,
    onNext: ChangeListener,
    onError?: ErrorListener
  ): () => void {
    if (!this.subscriptions.has(subscriptionId)) {
      this.subscriptions.set(subscriptionId, {
        listeners: [],
        snapshotListeners: [],
        errorListeners: [],
      });
    }

    const sub = this.subscriptions.get(subscriptionId)!;
    sub.listeners.push(onNext);
    if (onError) {
      sub.errorListeners.push(onError);
    }

    // Return unsubscribe function
    return () => {
      const idx = sub.listeners.indexOf(onNext);
      if (idx >= 0) sub.listeners.splice(idx, 1);
      if (onError) {
        const errIdx = sub.errorListeners.indexOf(onError);
        if (errIdx >= 0) sub.errorListeners.splice(errIdx, 1);
      }
    };
  }

  /**
   * Unsubscribe from a realtime listener.
   */
  async unsubscribe(subscriptionId: string): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const requestId = String(++this.requestId);
    const responsePromise = this.createPendingRequest(requestId, 5000);

    this.ws.send(JSON.stringify({
      type: 'unsubscribe',
      requestId,
      subscriptionId,
    }));

    try {
      await responsePromise;
      this.subscriptions.delete(subscriptionId);
    } catch (error) {
      // Silently fail — just remove subscription
      this.subscriptions.delete(subscriptionId);
    }
  }

  /**
   * Send a ping/pong to keep connection alive.
   */
  ping(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }

  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);

      // Handle pong
      if (message.type === 'pong') {
        return;
      }

      // Handle subscription response
      if (message.type === 'subscribed' && message.requestId) {
        const pending = this.pendingRequests.get(message.requestId);
        if (pending) {
          pending.resolve(message);
          this.pendingRequests.delete(message.requestId);
        }
        return;
      }

      // Handle unsubscribe response
      if (message.type === 'unsubscribed' && message.requestId) {
        const pending = this.pendingRequests.get(message.requestId);
        if (pending) {
          pending.resolve(message);
          this.pendingRequests.delete(message.requestId);
        }
        return;
      }

      // Handle errors
      if (message.type === 'error' && message.requestId) {
        const pending = this.pendingRequests.get(message.requestId);
        if (pending) {
          pending.reject(new Error(`${message.code}: ${message.message}`));
          this.pendingRequests.delete(message.requestId);
        }

        // Also notify error listeners
        if (message.subscriptionId) {
          const sub = this.subscriptions.get(message.subscriptionId);
          if (sub) {
            const error = new Error(`${message.code}: ${message.message}`);
            sub.errorListeners.forEach(listener => listener(error));
          }
        }
        return;
      }

      // Handle data changes
      if (message.type === 'change' && message.subscriptionId) {
        const sub = this.subscriptions.get(message.subscriptionId);
        if (sub) {
          const change: RealtimeChange = {
            subscriptionId: message.subscriptionId,
            event: message.event,
            data: message.data,
            version: message.version,
          };
          sub.listeners.forEach(listener => listener(change));
        }
      }
    } catch (error) {
      console.error('Failed to handle realtime message:', error);
    }
  }

  private createPendingRequest(
    requestId: string,
    timeoutMs = 10000
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId);
        reject(new Error(`Request ${requestId} timed out`));
      }, timeoutMs);

      this.pendingRequests.set(requestId, { resolve, reject, timeout });
    });
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    const jitteredDelay = delay + (Math.random() - 0.5) * delay * 0.1;

    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, jitteredDelay);
  }

  /**
   * Check if WebSocket is currently connected.
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
