import { useState, useEffect } from 'react';
import { apiClient } from '@/tools/api/client';

export interface WebhookTool {
  id: string;
  user_id: string;
  name: string;
  description: string;
  webhook_url: string;
  method: string;
  headers: Record<string, string>;
  input_schema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  auth_type: string | null;
  timeout_seconds: number;
  max_retries: number;
  is_enabled: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CreateWebhookToolPayload {
  name: string;
  description: string;
  webhook_url: string;
  method?: string;
  headers?: Record<string, string>;
  input_schema: any;
  auth_type?: string | null;
  auth_value?: string | null;
  timeout_seconds?: number;
  max_retries?: number;
  is_enabled?: boolean;
}

export interface UpdateWebhookToolPayload extends Partial<CreateWebhookToolPayload> {}

export function useWebhookTools() {
  const [tools, setTools] = useState<WebhookTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTools = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get<WebhookTool[]>('/webhook-tools');
      setTools(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al cargar herramientas');
      console.error('Error fetching webhook tools:', err);
    } finally {
      setLoading(false);
    }
  };

  const createTool = async (payload: CreateWebhookToolPayload) => {
    try {
      const response = await apiClient.post<WebhookTool>('/webhook-tools', payload);
      setTools((prev) => [response.data, ...prev]);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al crear herramienta');
      throw err;
    }
  };

  const updateTool = async (toolId: string, payload: UpdateWebhookToolPayload) => {
    try {
      const response = await apiClient.put<WebhookTool>(
        `/webhook-tools/${toolId}`,
        payload
      );
      setTools((prev) =>
        prev.map((tool) => (tool.id === toolId ? response.data : tool))
      );
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al actualizar herramienta');
      throw err;
    }
  };

  const deleteTool = async (toolId: string) => {
    try {
      await apiClient.delete(`/webhook-tools/${toolId}`);
      setTools((prev) => prev.filter((tool) => tool.id !== toolId));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al eliminar herramienta');
      throw err;
    }
  };

  useEffect(() => {
    fetchTools();
  }, []);

  return {
    tools,
    loading,
    error,
    fetchTools,
    createTool,
    updateTool,
    deleteTool,
  };
}
