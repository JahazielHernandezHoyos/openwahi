/**
 * AI Assistant API Service
 * Handles all API calls for AI Assistant configuration and management
 */

import { apiClient } from "@/tools/api/client";
import { AI_SANDBOX_TIMEOUT_MS } from "../config";
import type {
  AIConfig,
  AIConfigCreate,
  AIConfigUpdate,
  AIConversation,
  TestMessageRequest,
  TestMessageResponse,
  KnowledgeBase,
  WidgetToken,
  WidgetTokenCreate,
} from "../types";

export const aiAssistantApi = {
  /**
   * Get available AI providers
   */
  getProviders: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>("/ai-assistant/providers");
    return response.data;
  },

  /**
   * Get available models for a provider
   */
  getProviderModels: async (provider: string): Promise<string[]> => {
    const response = await apiClient.get<string[]>(
      `/ai-assistant/providers/${provider}/models`,
    );
    return response.data;
  },

  /**
   * Create a new AI configuration for a device
   */
  createConfig: async (
    deviceId: string,
    config: AIConfigCreate,
  ): Promise<AIConfig> => {
    const response = await apiClient.post<AIConfig>(
      `/ai-assistant/devices/${deviceId}/configs`,
      config,
    );
    return response.data;
  },

  /**
   * List all AI configurations for a device
   */
  listConfigs: async (deviceId: string): Promise<AIConfig[]> => {
    const response = await apiClient.get<AIConfig[]>(
      `/ai-assistant/devices/${deviceId}/configs`,
    );
    return response.data;
  },

  /**
   * Get a specific AI configuration
   */
  getConfig: async (configId: string): Promise<AIConfig> => {
    const response = await apiClient.get<AIConfig>(
      `/ai-assistant/configs/${configId}`,
    );
    return response.data;
  },

  /**
   * Update an AI configuration
   */
  updateConfig: async (
    configId: string,
    updates: AIConfigUpdate,
  ): Promise<AIConfig> => {
    const response = await apiClient.patch<AIConfig>(
      `/ai-assistant/configs/${configId}`,
      updates,
    );
    return response.data;
  },

  /**
   * Toggle AI configuration on/off
   */
  toggleConfig: async (
    configId: string,
    enabled: boolean,
  ): Promise<{ success: boolean; message: string; config: AIConfig }> => {
    const response = await apiClient.post<{
      success: boolean;
      message: string;
      config: AIConfig;
    }>(`/ai-assistant/configs/${configId}/toggle`, null, {
      params: { enabled },
    });
    return response.data;
  },

  /**
   * Delete an AI configuration
   */
  deleteConfig: async (configId: string): Promise<void> => {
    await apiClient.delete(`/ai-assistant/configs/${configId}`);
  },

  /**
   * Test an AI configuration without saving to history
   */
  testConfig: async (
    configId: string,
    request: TestMessageRequest,
  ): Promise<TestMessageResponse> => {
    try {
      const response = await apiClient.post<TestMessageResponse>(
        `/ai-assistant/configs/${configId}/test`,
        request,
        { timeout: AI_SANDBOX_TIMEOUT_MS },
      );
      return response.data;
    } catch (error) {
      if (
        typeof error === "object" &&
        error !== null &&
        "code" in error &&
        error.code === "ECONNABORTED"
      ) {
        throw new Error(
          "La prueba tardó más de lo esperado. El modelo local puede estar iniciando; inténtalo de nuevo.",
        );
      }
      throw error;
    }
  },

  /**
   * Get conversation history with a phone number
   */
  getConversationHistory: async (
    configId: string,
    phone: string,
  ): Promise<AIConversation> => {
    const response = await apiClient.get<AIConversation>(
      `/ai-assistant/configs/${configId}/conversations/${phone}`,
    );
    return response.data;
  },

  /**
   * Get all knowledge bases for the current user
   * Used for RAG configuration in AI Assistant
   */
  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await apiClient.get<KnowledgeBase[]>("/knowledge-base");
    return response.data;
  },

  // ── Standalone configs (no WhatsApp device required) ───────────────────

  /**
   * Create a standalone AI config (not tied to a WhatsApp device)
   */
  createStandaloneConfig: async (config: AIConfigCreate): Promise<AIConfig> => {
    const response = await apiClient.post<AIConfig>("/ai-assistant/configs", config);
    return response.data;
  },

  /**
   * List all AI configs for the current user (device-bound + standalone)
   */
  listAllConfigs: async (): Promise<AIConfig[]> => {
    const response = await apiClient.get<AIConfig[]>("/ai-assistant/configs");
    return response.data;
  },

  // ── Widget token management ────────────────────────────────────────────

  /**
   * Create a widget token linked to an AI config
   */
  createWidgetToken: async (data: WidgetTokenCreate): Promise<WidgetToken> => {
    const response = await apiClient.post<WidgetToken>("/widget/tokens", data);
    return response.data;
  },

  /**
   * List all widget tokens for the current user
   */
  listWidgetTokens: async (): Promise<WidgetToken[]> => {
    const response = await apiClient.get<WidgetToken[]>("/widget/tokens");
    return response.data;
  },

  /**
   * Revoke (deactivate) a widget token
   */
  revokeWidgetToken: async (tokenId: string): Promise<void> => {
    await apiClient.post(`/widget/tokens/${tokenId}/revoke`);
  },

  /**
   * Delete a widget token permanently
   */
  deleteWidgetToken: async (tokenId: string): Promise<void> => {
    await apiClient.delete(`/widget/tokens/${tokenId}`);
  },
};
