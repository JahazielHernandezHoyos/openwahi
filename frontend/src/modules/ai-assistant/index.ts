/**
 * AI Assistant Module
 * Exports all components, hooks, services, and types
 */

// Components
export { AIConfigPanel } from "./components/AIConfigPanel";
export { AIConfigDialog } from "./components/AIConfigDialog";
export { AITestDialog } from "./components/AITestDialog";

// Hooks
export {
  useAIConfigs,
  useAIConfig,
  useCreateAIConfig,
  useUpdateAIConfig,
  useToggleAIConfig,
  useDeleteAIConfig,
  useTestAIConfig,
  useAIProviders,
  useProviderModels,
  useConversationHistory,
} from "./hooks/useAIAssistant";

// Services
export { aiAssistantApi } from "./services/aiAssistantApi";

// Types
export type {
  AIProvider,
  AIConfig,
  AIConfigCreate,
  AIConfigUpdate,
  AIMessage,
  AIConversation,
  TestMessageRequest,
  TestMessageResponse,
} from "./types";

export { AVAILABLE_PROVIDERS, DEFAULT_PROMPTS } from "./types";
