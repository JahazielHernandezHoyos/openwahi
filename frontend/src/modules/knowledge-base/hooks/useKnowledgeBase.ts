/**
 * Knowledge Base hooks using React Query
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeBaseApi } from "../services/knowledgeBaseApi";
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseUpdate,
  KnowledgeDocument,
  SearchRequest,
} from "../types";

// Query keys
export const knowledgeBaseKeys = {
  all: ["knowledge-bases"] as const,
  lists: () => [...knowledgeBaseKeys.all, "list"] as const,
  list: (includeInactive: boolean) =>
    [...knowledgeBaseKeys.lists(), { includeInactive }] as const,
  details: () => [...knowledgeBaseKeys.all, "detail"] as const,
  detail: (id: string) => [...knowledgeBaseKeys.details(), id] as const,
  documents: (kbId: string) =>
    [...knowledgeBaseKeys.detail(kbId), "documents"] as const,
  document: (kbId: string, docId: string) =>
    [...knowledgeBaseKeys.documents(kbId), docId] as const,
  chunks: (kbId: string, docId: string) =>
    [...knowledgeBaseKeys.document(kbId, docId), "chunks"] as const,
};

// List knowledge bases
export function useKnowledgeBases(includeInactive = false) {
  return useQuery({
    queryKey: knowledgeBaseKeys.list(includeInactive),
    queryFn: () => knowledgeBaseApi.listKnowledgeBases(includeInactive),
  });
}

// Get single knowledge base
export function useKnowledgeBase(id: string) {
  return useQuery({
    queryKey: knowledgeBaseKeys.detail(id),
    queryFn: () => knowledgeBaseApi.getKnowledgeBase(id),
    enabled: !!id,
  });
}

// Create knowledge base
export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: KnowledgeBaseCreate) =>
      knowledgeBaseApi.createKnowledgeBase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
    },
  });
}

// Update knowledge base
export function useUpdateKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: KnowledgeBaseUpdate }) =>
      knowledgeBaseApi.updateKnowledgeBase(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
    },
  });
}

// Delete knowledge base
export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => knowledgeBaseApi.deleteKnowledgeBase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
    },
  });
}

// Toggle knowledge base active status
export function useToggleKnowledgeBase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      knowledgeBaseApi.toggleKnowledgeBase(id, isActive),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
    },
  });
}

// List documents in a knowledge base
export function useKnowledgeBaseDocuments(kbId: string) {
  return useQuery({
    queryKey: knowledgeBaseKeys.documents(kbId),
    queryFn: () => knowledgeBaseApi.listDocuments(kbId),
    enabled: !!kbId,
  });
}

// Upload document
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ kbId, file }: { kbId: string; file: File }) =>
      knowledgeBaseApi.uploadDocument(kbId, file),
    onSuccess: (_, { kbId }) => {
      queryClient.invalidateQueries({
        queryKey: knowledgeBaseKeys.documents(kbId),
      });
      queryClient.invalidateQueries({
        queryKey: knowledgeBaseKeys.detail(kbId),
      });
    },
  });
}

// Delete document
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ kbId, docId }: { kbId: string; docId: string }) =>
      knowledgeBaseApi.deleteDocument(kbId, docId),
    onSuccess: (_, { kbId }) => {
      queryClient.invalidateQueries({
        queryKey: knowledgeBaseKeys.documents(kbId),
      });
      queryClient.invalidateQueries({
        queryKey: knowledgeBaseKeys.detail(kbId),
      });
    },
  });
}

// Reprocess document
export function useReprocessDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ kbId, docId }: { kbId: string; docId: string }) =>
      knowledgeBaseApi.reprocessDocument(kbId, docId),
    onSuccess: (_, { kbId }) => {
      queryClient.invalidateQueries({
        queryKey: knowledgeBaseKeys.documents(kbId),
      });
    },
  });
}

// List document chunks
export function useDocumentChunks(
  kbId: string,
  docId: string,
  limit = 100,
  offset = 0
) {
  return useQuery({
    queryKey: [...knowledgeBaseKeys.chunks(kbId, docId), { limit, offset }],
    queryFn: () => knowledgeBaseApi.listDocumentChunks(kbId, docId, limit, offset),
    enabled: !!kbId && !!docId,
  });
}

// Search knowledge base
export function useSearchKnowledgeBase() {
  return useMutation({
    mutationFn: ({ kbId, request }: { kbId: string; request: SearchRequest }) =>
      knowledgeBaseApi.searchKnowledgeBase(kbId, request),
  });
}

// Search all knowledge bases
export function useSearchAllKnowledgeBases() {
  return useMutation({
    mutationFn: (request: SearchRequest) =>
      knowledgeBaseApi.searchAllKnowledgeBases(request),
  });
}
