/**
 * Custom hooks for AI Assistant functionality
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/AuthContext";
import { aiAssistantApi } from "../services/aiAssistantApi";
import type {
  AIConfigCreate,
  AIConfigUpdate,
  TestMessageRequest,
  WidgetTokenCreate,
} from "../types";

/**
 * Hook to fetch all AI configurations for a device
 */
export function useAIConfigs(deviceId: string | null) {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["ai-configs", deviceId],
    queryFn: () => aiAssistantApi.listConfigs(deviceId!),
    enabled: !!deviceId && !!user,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to fetch a single AI configuration
 */
export function useAIConfig(configId: string | null) {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["ai-config", configId],
    queryFn: () => aiAssistantApi.getConfig(configId!),
    enabled: !!configId && !!user,
  });
}

/**
 * Hook to create a new AI configuration
 */
export function useCreateAIConfig(deviceId: string) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (config: AIConfigCreate) =>
      aiAssistantApi.createConfig(deviceId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-configs", deviceId] });
      toast({
        title: "✅ Configuración creada",
        description: "Tu bot de IA ha sido configurado exitosamente",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo crear la configuración",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to update an existing AI configuration
 */
export function useUpdateAIConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      configId,
      updates,
    }: {
      configId: string;
      updates: AIConfigUpdate;
    }) => aiAssistantApi.updateConfig(configId, updates),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      queryClient.invalidateQueries({ queryKey: ["ai-config", data.id] });
      toast({
        title: "✅ Configuración actualizada",
        description: "Los cambios se han guardado correctamente",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo actualizar la configuración",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to toggle AI configuration on/off
 */
export function useToggleAIConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      configId,
      enabled,
    }: {
      configId: string;
      enabled: boolean;
    }) => aiAssistantApi.toggleConfig(configId, enabled),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      queryClient.invalidateQueries({
        queryKey: ["ai-config", data.config.id],
      });
      toast({
        title: data.config.is_enabled
          ? "✅ Bot activado"
          : "⏸️ Bot desactivado",
        description: data.message,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo cambiar el estado",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to delete an AI configuration
 */
export function useDeleteAIConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (configId: string) => aiAssistantApi.deleteConfig(configId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-configs"] });
      toast({
        title: "🗑️ Configuración eliminada",
        description: "La configuración ha sido eliminada correctamente",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo eliminar la configuración",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to test an AI configuration
 */
export function useTestAIConfig() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      configId,
      message,
    }: {
      configId: string;
      message: string;
    }) => aiAssistantApi.testConfig(configId, { message }),
    onError: (error: any) => {
      toast({
        title: "❌ Error en prueba",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo probar la configuración",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to fetch available AI providers
 */
export function useAIProviders() {
  return useQuery({
    queryKey: ["ai-providers"],
    queryFn: () => aiAssistantApi.getProviders(),
    staleTime: Infinity, // Providers don't change often
  });
}

/**
 * Hook to fetch models for a specific provider
 */
export function useProviderModels(provider: string | null) {
  return useQuery({
    queryKey: ["ai-provider-models", provider],
    queryFn: () => aiAssistantApi.getProviderModels(provider!),
    enabled: !!provider,
    staleTime: Infinity, // Models don't change often
  });
}

/**
 * Hook to fetch conversation history
 */
export function useConversationHistory(
  configId: string | null,
  phone: string | null,
) {
  return useQuery({
    queryKey: ["ai-conversation", configId, phone],
    queryFn: () => aiAssistantApi.getConversationHistory(configId!, phone!),
    enabled: !!configId && !!phone,
  });
}

/**
 * Hook to fetch knowledge bases for RAG configuration
 */
export function useKnowledgeBases() {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["knowledge-bases"],
    queryFn: () => aiAssistantApi.getKnowledgeBases(),
    enabled: !!user,
    staleTime: 60000, // 1 minute
  });
}

// ── Standalone configs ─────────────────────────────────────────────────────

/**
 * Hook to fetch ALL configs for the current user (device-bound + standalone)
 */
export function useAllAIConfigs() {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["ai-configs-all"],
    queryFn: () => aiAssistantApi.listAllConfigs(),
    enabled: !!user,
    staleTime: 30000,
  });
}

/**
 * Hook to create a standalone AI config (no device required)
 */
export function useCreateStandaloneConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (config: AIConfigCreate) =>
      aiAssistantApi.createStandaloneConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-configs-all"] });
      toast({
        title: "✅ Config creado",
        description: "Tu asistente standalone ha sido creado exitosamente",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo crear el config",
        variant: "destructive",
      });
    },
  });
}

// ── Widget tokens ──────────────────────────────────────────────────────────

/**
 * Hook to fetch all widget tokens for the current user
 */
export function useWidgetTokens() {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["widget-tokens"],
    queryFn: () => aiAssistantApi.listWidgetTokens(),
    enabled: !!user,
    staleTime: 30000,
  });
}

/**
 * Hook to create a new widget token
 */
export function useCreateWidgetToken() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: WidgetTokenCreate) =>
      aiAssistantApi.createWidgetToken(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["widget-tokens"] });
      toast({
        title: "✅ Token creado",
        description: "Tu widget token ha sido generado exitosamente",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description:
          error.response?.data?.detail ||
          error.message ||
          "No se pudo crear el token",
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to revoke (deactivate) a widget token
 */
export function useRevokeWidgetToken() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (tokenId: string) => aiAssistantApi.revokeWidgetToken(tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["widget-tokens"] });
      toast({ title: "⏸️ Token revocado", description: "El widget dejará de funcionar" });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      });
    },
  });
}

/**
 * Hook to delete a widget token permanently
 */
export function useDeleteWidgetToken() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (tokenId: string) => aiAssistantApi.deleteWidgetToken(tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["widget-tokens"] });
      toast({ title: "🗑️ Token eliminado", description: "El token ha sido eliminado permanentemente" });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Error",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      });
    },
  });
}
