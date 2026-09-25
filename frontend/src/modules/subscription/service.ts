import { apiClient } from "@/tools/api/client";

export type Plan = "free" | "pro" | "enterprise";

export interface Subscription {
  id: string;
  user_id: string;
  plan: Plan;
  status: string;
  device_limit: number;
  created_at: string | null;
}

export async function getMySubscription(): Promise<Subscription> {
  const { data } = await apiClient.get<Subscription>("/subscriptions/me");
  return data;
}
