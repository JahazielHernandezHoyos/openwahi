/**
 * Types for AI Assistant module
 */

export interface AIProvider {
  id: string;
  name: string;
  models: string[];
}

export interface AIConfig {
  id: string;
  device_id: string | null;
  name: string | null;
  phone_number: string | null;
  provider: string;
  model: string;
  is_enabled: boolean;
  system_prompt: string | null;
  temperature: number;
  max_tokens: number;
  use_memory: boolean;
  memory_window: number;
  auto_enhance_prompt: boolean;
  // RAG / Knowledge Base settings
  use_knowledge_base: boolean;
  knowledge_base_ids: string[];
  rag_top_k: number;
  rag_min_score: number;
  created_at: string;
  updated_at: string | null;
}

export interface AIConfigCreate {
  name?: string;
  phone_number?: string;
  provider: string;
  model: string;
  api_key?: string;
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
  use_memory?: boolean;
  memory_window?: number;
  auto_enhance_prompt?: boolean;
  // RAG / Knowledge Base settings
  use_knowledge_base?: boolean;
  knowledge_base_ids?: string[];
  rag_top_k?: number;
  rag_min_score?: number;
}

export interface AIConfigUpdate {
  provider?: string;
  model?: string;
  api_key?: string;
  is_enabled?: boolean;
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
  use_memory?: boolean;
  memory_window?: number;
  auto_enhance_prompt?: boolean;
  // RAG / Knowledge Base settings
  use_knowledge_base?: boolean;
  knowledge_base_ids?: string[];
  rag_top_k?: number;
  rag_min_score?: number;
}

export interface AIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider: string | null;
  model: string | null;
  tokens_used: number | null;
  created_at: string;
}

export interface AIConversation {
  id: string;
  from_phone: string;
  message_count: number;
  started_at: string;
  last_message_at: string;
  messages: AIMessage[];
}

export interface TestMessageRequest {
  message: string;
}

export interface TestMessageResponse {
  success: boolean;
  response?: string;
  error?: string;
  tokens_used?: number;
  processing_time_ms?: number;
  provider?: string;
  model?: string;
}

// Knowledge Base types (for RAG integration)
export interface KnowledgeBase {
  id: string;
  user_id: string;
  device_id: string | null;
  name: string;
  description: string | null;
  is_active: boolean;
  total_documents: number;
  total_chunks: number;
  created_at: string;
}

export const AVAILABLE_PROVIDERS: Record<string, AIProvider> = {
  groq: {
    id: "groq",
    name: "Groq",
    models: [
      "llama-3.3-70b-versatile",
      "llama-3.1-8b-instant",
      "llama-guard-4-12b",
      "openai/gpt-oss-120b",
      "openai/gpt-oss-20b",
      "mixtral-8x7b-32768",
      "gemma2-9b-it",
      "qwen/qwen3-32b",
    ],
  },
  llamacpp: {
    id: "llamacpp",
    name: "Local Qwen (llama.cpp)",
    models: ["Qwen3.5-0.8B-Q8_0"],
  },
};

export const DEFAULT_PROMPTS = {
  generic:
    "Eres un asistente útil y amigable de WhatsApp. Ayuda al usuario con sus preguntas y necesidades.",
  customer_service:
    "Eres un agente de servicio al cliente profesional y amable. Tu objetivo es ayudar a los clientes a resolver sus problemas y responder sus preguntas. Mantén un tono cortés, empático y resolutivo.",
  sales:
    "Eres un asesor de ventas profesional y consultivo. Tu objetivo es entender las necesidades del cliente y ofrecer soluciones apropiadas. No seas agresivo, enfócate en construir relaciones y proporcionar valor.",
  technical_support:
    "Eres un especialista en soporte técnico paciente y claro. Tu objetivo es ayudar a los usuarios a resolver problemas técnicos. Explica las cosas de forma simple, paso a paso, sin usar jerga innecesaria.",
};

// ── Widget Token types ──────────────────────────────────────────────────────

export interface WidgetToken {
  id: string;
  user_id: string;
  ai_config_id: string;
  token: string;
  name: string;
  allowed_origins: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface WidgetTokenCreate {
  name: string;
  ai_config_id: string;
  allowed_origins?: string;
}
