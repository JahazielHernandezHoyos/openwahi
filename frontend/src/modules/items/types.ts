/**
 * Tipos para el módulo Items
 */

export interface Item {
  id: string
  user_id: string
  title: string
  description?: string | null
  created_at: string
  updated_at: string
}

export interface ItemCreate {
  title: string
  description?: string
}

export interface ItemUpdate {
  title?: string
  description?: string
}

export interface PaginatedItems {
  items: Item[]
  total: number
  limit: number
  offset: number
}
