import type { AuthTokens } from './types';
import { AuthError, OwnFirebaseError } from './errors';

export interface SessionOptions {
  storageKey?: string;
  autoRefreshMs?: number;
}

export class SessionManager {
  private tokens: AuthTokens | null = null;
  private storageKey: string;
  private autoRefreshMs: number;
  private refreshTimer: NodeJS.Timeout | null = null;
  private onRefreshCallback: ((tokens: AuthTokens) => Promise<void>) | null = null;
  private onExpireCallback: (() => void) | null = null;

  constructor(options?: SessionOptions) {
    this.storageKey = options?.storageKey ?? 'ownfirebase_session';
    this.autoRefreshMs = options?.autoRefreshMs ?? 5 * 60 * 1000; // 5 minutes before expiry
    this.loadFromStorage();
  }

  /**
   * Store authentication tokens.
   */
  setTokens(tokens: AuthTokens): void {
    this.tokens = tokens;
    this.saveToStorage();
    this.scheduleAutoRefresh();
  }

  /**
   * Get current access token.
   */
  getAccessToken(): string | null {
    return this.tokens?.access ?? null;
  }

  /**
   * Get current refresh token.
   */
  getRefreshToken(): string | null {
    return this.tokens?.refresh ?? null;
  }

  /**
   * Get current user ID.
   */
  getUserId(): string | null {
    return this.tokens?.user_id ?? null;
  }

  /**
   * Get current user email.
   */
  getUserEmail(): string | null {
    return this.tokens?.email ?? null;
  }

  /**
   * Get all current tokens.
   */
  getTokens(): AuthTokens | null {
    return this.tokens ? { ...this.tokens } : null;
  }

  /**
   * Check if user is authenticated.
   */
  isAuthenticated(): boolean {
    return !!this.tokens?.access;
  }

  /**
   * Clear all stored tokens and stop refresh timer.
   */
  clear(): void {
    this.tokens = null;
    this.clearAutoRefresh();
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(this.storageKey);
      }
    } catch (error) {
      console.warn('Failed to clear session storage:', error);
    }
  }

  /**
   * Set callback for token refresh events.
   */
  onRefresh(callback: (tokens: AuthTokens) => Promise<void>): void {
    this.onRefreshCallback = callback;
  }

  /**
   * Set callback for token expiration events.
   */
  onExpire(callback: () => void): void {
    this.onExpireCallback = callback;
  }

  /**
   * Trigger token refresh.
   */
  async refresh(): Promise<AuthTokens> {
    if (!this.tokens?.refresh) {
      throw new AuthError('No refresh token available', 'NO_REFRESH_TOKEN');
    }

    try {
      if (!this.onRefreshCallback) {
        throw new AuthError(
          'No refresh callback configured',
          'NO_REFRESH_CALLBACK'
        );
      }

      await this.onRefreshCallback(this.tokens);

      // Re-schedule refresh after getting new tokens
      this.scheduleAutoRefresh();

      return this.tokens;
    } catch (error) {
      this.clear();
      if (this.onExpireCallback) {
        this.onExpireCallback();
      }
      throw error;
    }
  }

  /**
   * Validate token format (basic check).
   */
  isTokenExpired(token: string): boolean {
    try {
      // JWT format: header.payload.signature
      const parts = token.split('.');
      if (parts.length !== 3) return true;

      // Decode payload (without verification)
      const payload = JSON.parse(
        Buffer.from(parts[1], 'base64').toString('utf8')
      );

      // Check expiration
      if (payload.exp) {
        const expiryTime = payload.exp * 1000; // Convert to milliseconds
        return Date.now() >= expiryTime;
      }

      return false;
    } catch (error) {
      console.warn('Failed to check token expiration:', error);
      return true;
    }
  }

  private scheduleAutoRefresh(): void {
    this.clearAutoRefresh();

    if (!this.tokens?.access || !this.onRefreshCallback) {
      return;
    }

    try {
      const parts = this.tokens.access.split('.');
      if (parts.length !== 3) return;

      const payload = JSON.parse(
        Buffer.from(parts[1], 'base64').toString('utf8')
      );

      if (!payload.exp) return;

      const expiryMs = payload.exp * 1000;
      const delayMs = Math.max(0, expiryMs - Date.now() - this.autoRefreshMs);

      this.refreshTimer = setTimeout(() => {
        this.refresh().catch(error => {
          console.error('Auto-refresh failed:', error);
        });
      }, delayMs);
    } catch (error) {
      console.warn('Failed to schedule auto-refresh:', error);
    }
  }

  private clearAutoRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  private saveToStorage(): void {
    try {
      if (typeof localStorage !== 'undefined' && this.tokens) {
        localStorage.setItem(this.storageKey, JSON.stringify(this.tokens));
      }
    } catch (error) {
      console.warn('Failed to save session to storage:', error);
    }
  }

  private loadFromStorage(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        const stored = localStorage.getItem(this.storageKey);
        if (stored) {
          this.tokens = JSON.parse(stored);
          // Validate tokens aren't expired
          if (this.tokens?.access && this.isTokenExpired(this.tokens.access)) {
            this.clear();
          }
        }
      }
    } catch (error) {
      console.warn('Failed to load session from storage:', error);
      this.clear();
    }
  }

  /**
   * Clean up resources.
   */
  destroy(): void {
    this.clearAutoRefresh();
  }
}
