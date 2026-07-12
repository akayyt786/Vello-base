import type { APIError } from './types';

export class OwnFirebaseError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly detail?: unknown;

  constructor(
    message: string,
    code: string = 'UNKNOWN_ERROR',
    status: number = 500,
    detail?: unknown
  ) {
    super(message);
    this.name = 'OwnFirebaseError';
    this.code = code;
    this.status = status;
    this.detail = detail;

    // Maintain proper stack trace
    Object.setPrototypeOf(this, OwnFirebaseError.prototype);
  }

  static fromAPIError(error: APIError): OwnFirebaseError {
    let code = 'UNKNOWN_ERROR';

    // Map HTTP status to error codes
    switch (error.status) {
      case 400:
        code = 'INVALID_ARGUMENT';
        break;
      case 401:
        code = 'UNAUTHENTICATED';
        break;
      case 403:
        code = 'PERMISSION_DENIED';
        break;
      case 404:
        code = 'NOT_FOUND';
        break;
      case 409:
        code = 'CONFLICT';
        break;
      case 429:
        code = 'RESOURCE_EXHAUSTED';
        break;
      case 500:
        code = 'INTERNAL';
        break;
      case 503:
        code = 'UNAVAILABLE';
        break;
      default:
        code = 'UNKNOWN_ERROR';
    }

    return new OwnFirebaseError(
      error.message || `HTTP ${error.status}`,
      code,
      error.status,
      error.detail
    );
  }

  static isAuthError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.code === 'UNAUTHENTICATED';
  }

  static isPermissionError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.code === 'PERMISSION_DENIED';
  }

  static isNotFoundError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.code === 'NOT_FOUND';
  }

  static isConflictError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.code === 'CONFLICT';
  }

  static isRateLimitError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.code === 'RESOURCE_EXHAUSTED';
  }

  static isServerError(error: unknown): boolean {
    return error instanceof OwnFirebaseError && error.status >= 500;
  }
}

export class AuthError extends OwnFirebaseError {
  constructor(message: string, code: string = 'AUTH_ERROR', detail?: unknown) {
    super(message, code, 401, detail);
    this.name = 'AuthError';
    Object.setPrototypeOf(this, AuthError.prototype);
  }
}

export class ValidationError extends OwnFirebaseError {
  constructor(message: string, detail?: unknown) {
    super(message, 'INVALID_ARGUMENT', 400, detail);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

export class NetworkError extends OwnFirebaseError {
  constructor(message: string, detail?: unknown) {
    super(message, 'NETWORK_ERROR', 0, detail);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}
