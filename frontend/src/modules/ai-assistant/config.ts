const DEFAULT_AI_SANDBOX_TIMEOUT_MS = 60_000;

export function resolveAISandboxTimeoutMs(value?: string): number {
  const timeout = Number(value);
  return Number.isFinite(timeout) && timeout > 0
    ? timeout
    : DEFAULT_AI_SANDBOX_TIMEOUT_MS;
}

export const AI_SANDBOX_TIMEOUT_MS = resolveAISandboxTimeoutMs(
  process.env.NEXT_PUBLIC_AI_SANDBOX_TIMEOUT_MS,
);
