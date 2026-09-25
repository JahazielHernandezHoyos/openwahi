'use client'

import { useEffect, useState } from 'react'

/**
 * Hook para detectar si el componente se ha montado en el cliente
 * Útil para evitar problemas de hidratación en Next.js
 */
export function useMounted() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return mounted
}

