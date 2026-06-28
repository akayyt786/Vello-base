export interface OwnFirebaseConfig {
  baseUrl: string;
  projectId?: string;
  accessToken?: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
  user_id: string;
  email?: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectMember {
  id: string;
  user: string;
  role: 'owner' | 'editor' | 'viewer';
  joined_at: string;
}

export interface DataDocument {
  id: string;
  collection: string;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DataCollection {
  id: string;
  name: string;
  document_count: number;
}

export interface FunctionDefinition {
  id: string;
  name: string;
  runtime: string;
  entry_point: string;
  source_code: string;
  is_active: boolean;
}

export interface FunctionInvocation {
  invocation_id: string;
  status: string;
  result?: unknown;
  error?: string;
  duration_ms?: number;
}

export interface FunctionLog {
  id: string;
  level: string;
  message: string;
  timestamp: string;
}

export interface StorageObject {
  id: string;
  name: string;
  size: number;
  content_type: string;
  url: string;
  created_at: string;
}

export interface StorageUploadUrl {
  upload_url: string;
  object_key: string;
  expires_at: string;
}

export interface PushDeviceToken {
  id: string;
  token: string;
  platform: 'ios' | 'android' | 'web';
  is_active: boolean;
}

export interface PushTopic {
  id: string;
  name: string;
  subscriber_count: number;
}

export interface AnalyticsEvent {
  id: string;
  name: string;
  params: Record<string, unknown>;
  timestamp: string;
  user_id?: string;
  session_id?: string;
}

export interface UserProperty {
  id: string;
  name: string;
  value: string;
  user_id: string;
}

export interface CrashReport {
  id: string;
  exception_type: string;
  message: string;
  stack_trace: string;
  occurred_at: string;
  app_version: string;
  platform: string;
}

export interface PerformanceTrace {
  id: string;
  name: string;
  duration_ms: number;
  started_at: string;
  attributes: Record<string, string>;
  metrics: Record<string, number>;
}

export interface RemoteConfigParameter {
  id: string;
  key: string;
  default_value: string;
  description: string;
  value_type: 'string' | 'boolean' | 'number' | 'json';
}

export interface Experiment {
  id: string;
  name: string;
  status: 'draft' | 'running' | 'paused' | 'completed';
  variants: ExperimentVariant[];
}

export interface ExperimentVariant {
  id: string;
  name: string;
  allocation: number;
  config: Record<string, unknown>;
}

export interface ExperimentAssignment {
  variant_name: string;
  config: Record<string, unknown>;
  experiment_name: string;
}

export interface VectorCollection {
  id: string;
  name: string;
  embedding_model: string;
  dimensions: number;
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  external_id: string;
  metadata?: Record<string, unknown>;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletion {
  content: string;
  model: string;
  provider: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface APIError {
  status: number;
  message: string;
  detail?: unknown;
}

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export interface WriteBatchOperation {
  op: 'set' | 'update' | 'delete';
  collection: string;
  doc_id?: string;
  data?: Record<string, unknown>;
}

export interface WriteBatchResult {
  written: number;
  errors: unknown[];
}

export interface AppCheckToken {
  token: string;
  expires_at: string;
}

export interface CustomToken {
  custom_token: string;
}

export interface LinkedSocialAccount {
  id: string;
  provider: string;
  provider_uid: string;
  email?: string;
  linked_at: string;
}

export interface MFADevice {
  id: string;
  type: 'totp' | 'sms';
  name: string;
  confirmed: boolean;
  created_at: string;
}
