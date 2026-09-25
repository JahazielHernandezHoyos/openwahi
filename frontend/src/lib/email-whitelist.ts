/**
 * Email Whitelist Utility
 * Verifica si un email está permitido para acceder a la plataforma
 */

/**
 * Verifica si un email está en la lista de correos permitidos
 * @param email - El email a verificar
 * @returns true si el email está permitido o si no hay whitelist configurada
 */
export function isEmailAllowed(email: string | undefined | null): boolean {
  // Si no hay email, no está permitido
  if (!email) {
    return false;
  }

  // Obtener la lista de emails permitidos desde las variables de entorno
  const allowedEmailsEnv = process.env.NEXT_PUBLIC_ALLOWED_EMAILS;

  // Si no hay whitelist configurada, permitir todos los emails
  if (!allowedEmailsEnv || allowedEmailsEnv.trim() === '') {
    return true;
  }

  // Convertir la lista de emails a un array y limpiar espacios
  const allowedEmails = allowedEmailsEnv
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter((e) => e.length > 0);

  // Verificar si el email está en la lista (case-insensitive)
  return allowedEmails.includes(email.toLowerCase());
}

/**
 * Obtiene la lista de emails permitidos
 * @returns Array de emails permitidos
 */
export function getAllowedEmails(): string[] {
  const allowedEmailsEnv = process.env.NEXT_PUBLIC_ALLOWED_EMAILS;

  if (!allowedEmailsEnv || allowedEmailsEnv.trim() === '') {
    return [];
  }

  return allowedEmailsEnv
    .split(',')
    .map((e) => e.trim())
    .filter((e) => e.length > 0);
}
