/**
 * Knowledge Base API service
 */

import { apiClient } from "@/tools/api/client";
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseUpdate,
  KnowledgeDocument,
  DocumentUploadResponse,
  SearchRequest,
  SearchResponse,
  DocumentChunk,
} from "../types";

const BASE_URL = "/knowledge-base";

export const knowledgeBaseApi = {
  // Knowledge Base CRUD
  async listKnowledgeBases(includeInactive = false): Promise<KnowledgeBase[]> {
    const params = new URLSearchParams();
    if (includeInactive) {
      params.append("include_inactive", "true");
    }
    const url = params.toString() ? `${BASE_URL}?${params}` : BASE_URL;
    const response = await apiClient.get<KnowledgeBase[]>(url);
    return response.data;
  },

  async getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    const response = await apiClient.get<KnowledgeBase>(`${BASE_URL}/${id}`);
    return response.data;
  },

  async createKnowledgeBase(data: KnowledgeBaseCreate): Promise<KnowledgeBase> {
    const response = await apiClient.post<KnowledgeBase>(BASE_URL, data);
    return response.data;
  },

  async updateKnowledgeBase(
    id: string,
    data: KnowledgeBaseUpdate
  ): Promise<KnowledgeBase> {
    const response = await apiClient.patch<KnowledgeBase>(`${BASE_URL}/${id}`, data);
    return response.data;
  },

  async deleteKnowledgeBase(id: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/${id}`);
  },

  async toggleKnowledgeBase(
    id: string,
    isActive: boolean
  ): Promise<{ success: boolean; message: string; knowledge_base: KnowledgeBase }> {
    const response = await apiClient.post<{ success: boolean; message: string; knowledge_base: KnowledgeBase }>(
      `${BASE_URL}/${id}/toggle?is_active=${isActive}`
    );
    return response.data;
  },

  // Document Management
  async listDocuments(kbId: string): Promise<KnowledgeDocument[]> {
    const response = await apiClient.get<KnowledgeDocument[]>(`${BASE_URL}/${kbId}/documents`);
    return response.data;
  },

  async getDocument(kbId: string, docId: string): Promise<KnowledgeDocument> {
    const response = await apiClient.get<KnowledgeDocument>(
      `${BASE_URL}/${kbId}/documents/${docId}`
    );
    return response.data;
  },

  async uploadDocument(
    kbId: string,
    file: File
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.post<DocumentUploadResponse>(
      `${BASE_URL}/${kbId}/documents`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  async deleteDocument(kbId: string, docId: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/${kbId}/documents/${docId}`);
  },

  async downloadDocument(kbId: string, docId: string, filename: string): Promise<void> {
    const response = await apiClient.get(`${BASE_URL}/${kbId}/documents/${docId}/download`, {
      responseType: 'blob',
    });

    // Create a download link and trigger it
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async reprocessDocument(
    kbId: string,
    docId: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `${BASE_URL}/${kbId}/documents/${docId}/reprocess`
    );
    return response.data;
  },

  async listDocumentChunks(
    kbId: string,
    docId: string,
    limit = 100,
    offset = 0
  ): Promise<DocumentChunk[]> {
    const response = await apiClient.get<DocumentChunk[]>(
      `${BASE_URL}/${kbId}/documents/${docId}/chunks?limit=${limit}&offset=${offset}`
    );
    return response.data;
  },

  // Search
  async searchKnowledgeBase(
    kbId: string,
    request: SearchRequest
  ): Promise<SearchResponse> {
    const response = await apiClient.post<SearchResponse>(`${BASE_URL}/${kbId}/query`, request);
    return response.data;
  },

  async searchAllKnowledgeBases(request: SearchRequest): Promise<SearchResponse> {
    const response = await apiClient.post<SearchResponse>(`${BASE_URL}/query-all`, request);
    return response.data;
  },
};
