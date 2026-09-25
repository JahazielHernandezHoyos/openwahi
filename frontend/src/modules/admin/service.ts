import { apiClient } from "@/tools/api/client";

export interface CurrentUser {
  id: string;
  email: string;
  created_at: string | null;
  is_admin: boolean;
}

export interface AdminStats {
  total_users: number;
  monthly_conversations: number;
  monthly_cost_usd: number;
  year: number;
  month: number;
  plan_counts: Record<string, number>;
}

export interface AdminUser {
  user_id: string;
  email?: string;
  plan: "free" | "pro" | "enterprise";
  status: string;
  monthly_conversations: number;
  monthly_cost_usd: number;
  created_at: string | null;
}

export interface MonthlyUsage {
  year: number;
  month: number;
  conversations: number;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
}

export interface MonthlyCost {
  year: number;
  month: number;
  provider: string;
  cost_usd: number;
}

export interface AIChainEntry {
  id: string;
  position: number;
  provider_name: string;
  model: string;
  base_url: string | null;
  requires_tools: boolean;
  is_enabled: boolean;
  is_healthy: boolean;
  consecutive_failures: number;
  last_error: string | null;
  last_probe_at: string | null;
  last_probe_latency_ms: number | null;
  has_api_key: boolean;
  summary_24h: {
    calls: number;
    failures: number;
    cost_usd: number;
  };
}

export type AIChainEventType =
  | "failure"
  | "recovery"
  | "probe_ok"
  | "probe_fail"
  | "circuit_open"
  | "circuit_close";

export interface AIChainEvent {
  id: string;
  entry_id: string;
  event_type: AIChainEventType;
  error: string | null;
  latency_ms: number | null;
  created_at: string;
}

export interface CreateAIChainEntryInput {
  provider_name: string;
  base_url?: string;
  model: string;
  api_key?: string;
  requires_tools: boolean;
  position?: number;
}

export interface UpdateAIChainEntryInput {
  model?: string;
  base_url?: string | null;
  api_key?: string;
  requires_tools?: boolean;
  is_enabled?: boolean;
  is_healthy?: boolean;
  position?: number;
}

export interface AIProbeResult {
  ok: boolean;
  latency_ms: number;
  error?: string;
}

interface SuccessResponse {
  success: boolean;
}

export const adminApi = {
  getCurrentUser: async (): Promise<CurrentUser> => {
    const { data } = await apiClient.get("/auth/me");
    return data;
  },
  getStats: async (): Promise<AdminStats> => {
    const { data } = await apiClient.get("/internal/admin/stats");
    return data;
  },
  getUsers: async (): Promise<AdminUser[]> => {
    const { data } = await apiClient.get("/internal/admin/users");
    return data;
  },
  getUserUsage: async (userId: string): Promise<MonthlyUsage[]> => {
    const { data } = await apiClient.get(`/internal/admin/users/${userId}/usage`);
    return data;
  },
  updateUserPlan: async (userId: string, plan: string): Promise<{ success: boolean }> => {
    const { data } = await apiClient.patch(`/internal/admin/users/${userId}/plan`, { plan });
    return data;
  },
  toggleSubscription: async (userId: string): Promise<{ success: boolean; new_status: string }> => {
    const { data } = await apiClient.patch(`/internal/admin/users/${userId}/subscription/toggle`, {});
    return data;
  },
  getCosts: async (): Promise<MonthlyCost[]> => {
    const { data } = await apiClient.get("/internal/admin/costs");
    return data;
  },
  getAIChain: async (): Promise<AIChainEntry[]> => {
    const { data } = await apiClient.get("/internal/admin/ai-chain");
    return data;
  },
  createAIChainEntry: async (
    input: CreateAIChainEntryInput
  ): Promise<SuccessResponse & { id: string }> => {
    const { data } = await apiClient.post("/internal/admin/ai-chain", input);
    return data;
  },
  updateAIChainEntry: async (
    id: string,
    input: UpdateAIChainEntryInput
  ): Promise<SuccessResponse> => {
    const { data } = await apiClient.patch(`/internal/admin/ai-chain/${id}`, input);
    return data;
  },
  deleteAIChainEntry: async (id: string): Promise<SuccessResponse> => {
    const { data } = await apiClient.delete(`/internal/admin/ai-chain/${id}`);
    return data;
  },
  reorderAIChain: async (orderedIds: string[]): Promise<SuccessResponse> => {
    const { data } = await apiClient.post("/internal/admin/ai-chain/reorder", {
      ordered_ids: orderedIds,
    });
    return data;
  },
  probeAIChainEntry: async (id: string): Promise<AIProbeResult> => {
    const { data } = await apiClient.post(`/internal/admin/ai-chain/${id}/probe`);
    return data;
  },
  getAIChainEvents: async (limit = 100): Promise<AIChainEvent[]> => {
    const { data } = await apiClient.get("/internal/admin/ai-chain/events", {
      params: { limit },
    });
    return data;
  },
};
