export interface ApiToken {
  id: string;
  name: string;
  token_prefix: string;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiTokenCreated {
  id: string;
  name: string;
  token: string;
  token_prefix: string;
  created_at: string;
}

export interface ApiTokenListResponse {
  tokens: ApiToken[];
  total: number;
}

export interface WebhookConfig {
  id: string;
  url: string;
  has_secret: boolean;
  is_active: boolean;
  last_triggered_at: string | null;
  failure_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface WebhookTestResult {
  success: boolean;
  status_code: number | null;
  message: string;
  response_time_ms: number | null;
}

export interface WebhookConfigCreate {
  url: string;
  secret?: string;
  is_active: boolean;
}
