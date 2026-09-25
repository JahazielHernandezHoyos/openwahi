import { apiClient } from "@/tools/api/client";
import {
  ApiToken,
  ApiTokenCreated,
  ApiTokenListResponse,
  WebhookConfig,
  WebhookConfigCreate,
  WebhookTestResult,
} from "../types";

export const developerApi = {
  // API Tokens
  async getTokens(): Promise<ApiTokenListResponse> {
    const response = await apiClient.get<ApiTokenListResponse>("/developer/tokens");
    return response.data;
  },

  async createToken(name: string): Promise<ApiTokenCreated> {
    const response = await apiClient.post<ApiTokenCreated>("/developer/tokens", { name });
    return response.data;
  },

  async revokeToken(tokenId: string): Promise<void> {
    await apiClient.delete(`/developer/tokens/${tokenId}`);
  },

  // Webhook
  async getWebhook(): Promise<WebhookConfig | null> {
    try {
      const response = await apiClient.get<WebhookConfig>("/developer/webhook");
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  async upsertWebhook(config: WebhookConfigCreate): Promise<WebhookConfig> {
    const response = await apiClient.put<WebhookConfig>("/developer/webhook", config);
    return response.data;
  },

  async deleteWebhook(): Promise<void> {
    await apiClient.delete("/developer/webhook");
  },

  async testWebhook(): Promise<WebhookTestResult> {
    const response = await apiClient.post<WebhookTestResult>("/developer/webhook/test");
    return response.data;
  },
};
