import { apiClient } from '@/tools/api/client'
import { Item, ItemCreate, ItemUpdate, PaginatedItems } from '../types'

/**
 * API service para operaciones CRUD de Items
 */
export const itemsApi = {
  /**
   * Obtiene todos los items del usuario actual
   */
  getAll: async (): Promise<Item[]> => {
    const response = await apiClient.get<PaginatedItems>('/items/')
    return response.data.items
  },

  /**
   * Obtiene items paginados
   */
  getPaginated: async (limit = 50, offset = 0): Promise<PaginatedItems> => {
    const response = await apiClient.get<PaginatedItems>(`/items/?limit=${limit}&offset=${offset}`)
    return response.data
  },

  /**
   * Obtiene un item por ID
   */
  getById: async (id: string): Promise<Item> => {
    const response = await apiClient.get<Item>(`/items/${id}`)
    return response.data
  },

  /**
   * Crea un nuevo item
   */
  create: async (data: ItemCreate): Promise<Item> => {
    const response = await apiClient.post<Item>('/items/', data)
    return response.data
  },

  /**
   * Actualiza un item existente
   */
  update: async (id: string, data: ItemUpdate): Promise<Item> => {
    const response = await apiClient.put<Item>(`/items/${id}`, data)
    return response.data
  },

  /**
   * Elimina un item
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/items/${id}`)
  },
}
