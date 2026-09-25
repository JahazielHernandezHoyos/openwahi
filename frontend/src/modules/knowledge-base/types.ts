/**
 * Knowledge Base types matching backend schemas
 */

export interface KnowledgeBase {
  id: string;
  user_id: string;
  device_id: string | null;
  name: string;
  description: string | null;
  is_active: boolean;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
  created_at: string;
  updated_at: string | null;
}

export interface KnowledgeBaseCreate {
  name: string;
  description?: string;
  device_id?: string;
  embedding_model?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface KnowledgeBaseUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  chunk_size?: number;
  chunk_overlap?: number;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  error_message: string | null;
  total_chunks: number;
  total_tokens: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
  processed_at: string | null;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_size_bytes: number;
  status: string;
  message: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  min_score?: number;
  knowledge_base_ids?: string[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  query_time_ms: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  token_count: number;
  metadata: Record<string, unknown>;
}
