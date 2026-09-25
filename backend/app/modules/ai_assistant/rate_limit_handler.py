"""
Rate Limit Handler para AI Assistant.

Maneja rate limits de forma inteligente con:
- Reintentos exponenciales con backoff
- Respeto del header retry-after
- Fallback a modelos más económicos
- Queue de reintentos
- Mensajes informativos al usuario
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Excepción personalizada para rate limits."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        provider: str = None,
        model: str = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.provider = provider
        self.model = model


class RateLimitHandler:
    """
    Manejador de rate limits con estrategias de reintento y fallback.
    """

    # Mapeo de modelos por velocidad/economía (del más económico al más costoso)
    FALLBACK_MODELS = {
        "groq": [
            "llama-3.1-8b-instant",  # Más rápido y económico
            "openai/gpt-oss-20b",  # Alternativa rápida
            "llama-3.3-70b-versatile",  # Original
            "openai/gpt-oss-120b",  # Más potente
        ],
    }

    # Configuración de reintentos
    MAX_RETRIES = 3
    BASE_DELAY = 2.0  # segundos
    MAX_DELAY = 60.0  # segundos
    EXPONENTIAL_BASE = 2

    @staticmethod
    def _calculate_backoff_delay(attempt: int, base_delay: float = BASE_DELAY) -> float:
        """
        Calcula el delay con exponential backoff.

        Formula: min(base_delay * (2 ^ attempt), MAX_DELAY)

        Args:
            attempt: Número de intento (0-indexed)
            base_delay: Delay base en segundos

        Returns:
            Delay en segundos
        """
        delay = base_delay * (RateLimitHandler.EXPONENTIAL_BASE**attempt)
        return min(delay, RateLimitHandler.MAX_DELAY)

    @staticmethod
    def _extract_retry_after(error_message: str) -> Optional[float]:
        """
        Extrae el tiempo de espera del mensaje de error.

        Groq incluye mensajes como:
        "Please try again in 5.649999999s"
        "Please try again in 45s"

        Args:
            error_message: Mensaje de error del proveedor

        Returns:
            Segundos a esperar o None
        """
        import re

        # Buscar patrón: "try again in X.XXs" o "try again in Xs"
        match = re.search(r"try again in ([\d.]+)s", error_message)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return None

    @staticmethod
    def _parse_rate_limit_error(error: Exception) -> Dict:
        """
        Parsea un error de rate limit para extraer información útil.

        Args:
            error: Excepción del proveedor

        Returns:
            Dict con información del error
        """
        error_str = str(error)

        return {
            "is_rate_limit": "rate_limit" in error_str.lower()
            or "429" in error_str
            or "too many requests" in error_str.lower(),
            "retry_after": RateLimitHandler._extract_retry_after(error_str),
            "message": error_str,
            "is_token_limit": "TPM" in error_str or "tokens per minute" in error_str,
            "is_request_limit": "RPM" in error_str
            or "requests per minute" in error_str,
        }

    @staticmethod
    def _get_fallback_model(
        provider: str, current_model: str
    ) -> Optional[tuple[str, str]]:
        """
        Obtiene un modelo de fallback más económico.

        Args:
            provider: Proveedor actual
            current_model: Modelo actual que falló

        Returns:
            Tuple (provider, model) de fallback o None
        """
        if provider not in RateLimitHandler.FALLBACK_MODELS:
            return None

        available_models = RateLimitHandler.FALLBACK_MODELS[provider]

        # Buscar el índice del modelo actual
        try:
            current_index = available_models.index(current_model)
        except ValueError:
            # Modelo no está en la lista, usar el primero (más económico)
            return (provider, available_models[0])

        # Si ya estamos en el modelo más económico, no hay fallback
        if current_index == 0:
            logger.warning(
                f"Already using cheapest model {current_model}, no fallback available"
            )
            return None

        # Usar el modelo anterior (más económico)
        fallback_model = available_models[current_index - 1]
        logger.info(
            f"Falling back from {current_model} to {fallback_model} (cheaper/faster)"
        )
        return (provider, fallback_model)

    @staticmethod
    async def execute_with_retry(
        func,
        provider: str,
        model: str,
        max_retries: int = MAX_RETRIES,
        enable_fallback: bool = True,
    ):
        """
        Ejecuta una función con manejo inteligente de rate limits.

        Estrategias:
        1. Reintento con exponential backoff
        2. Respeto del retry-after del proveedor
        3. Fallback a modelo más económico si sigue fallando
        4. Mensajes informativos en logs

        Args:
            func: Función async a ejecutar
            provider: Proveedor de IA
            model: Modelo actual
            max_retries: Máximo de reintentos
            enable_fallback: Si debe hacer fallback a modelo más económico

        Returns:
            Resultado de la función

        Raises:
            Exception: Si falla después de todos los reintentos
        """
        attempt = 0
        current_provider = provider
        current_model = model
        last_error = None

        while attempt <= max_retries:
            try:
                # Ejecutar la función
                if attempt > 0:
                    logger.info(
                        f"🔄 Retry attempt {attempt}/{max_retries} with {current_provider}/{current_model}"
                    )

                return await func(current_provider, current_model)

            except Exception as e:
                last_error = e
                error_info = RateLimitHandler._parse_rate_limit_error(e)

                # Si NO es rate limit, fallar inmediatamente
                if not error_info["is_rate_limit"]:
                    logger.error(f"❌ Non-rate-limit error: {e}")
                    raise

                # Es rate limit, manejar inteligentemente
                logger.warning(f"⚠️ Rate limit hit: {error_info['message'][:200]}")

                # Si ya agotamos los reintentos, intentar fallback
                if attempt >= max_retries:
                    if enable_fallback:
                        fallback = RateLimitHandler._get_fallback_model(
                            current_provider, current_model
                        )
                        if fallback:
                            logger.info(
                                f"🔀 Attempting fallback: {fallback[0]}/{fallback[1]}"
                            )
                            current_provider, current_model = fallback
                            attempt = 0  # Reset attempts for fallback model
                            continue

                    logger.error(
                        f"❌ Rate limit exceeded after {max_retries} retries and no fallback available"
                    )
                    raise RateLimitError(
                        f"Rate limit exceeded after {max_retries} retries. "
                        f"Provider: {provider}, Model: {model}. "
                        f"Please try again later or upgrade your plan.",
                        retry_after=error_info["retry_after"],
                        provider=provider,
                        model=model,
                    ) from e

                # Calcular delay
                if error_info["retry_after"]:
                    # Usar el retry-after del proveedor
                    delay = error_info["retry_after"]
                    logger.info(
                        f"⏱️  Provider suggests waiting {delay:.2f}s (from retry-after)"
                    )
                else:
                    # Usar exponential backoff
                    delay = RateLimitHandler._calculate_backoff_delay(attempt)
                    logger.info(
                        f"⏱️  Waiting {delay:.2f}s (exponential backoff, attempt {attempt + 1})"
                    )

                # Información adicional
                if error_info["is_token_limit"]:
                    logger.info(
                        "💡 Token limit hit - Consider reducing max_tokens or using a cheaper model"
                    )
                elif error_info["is_request_limit"]:
                    logger.info(
                        "💡 Request limit hit - Consider adding delays between requests"
                    )

                # Esperar antes de reintentar
                logger.info(f"⏳ Waiting {delay:.2f}s before retry...")
                await asyncio.sleep(delay)

                attempt += 1

        # Si llegamos aquí, algo salió mal
        raise last_error


class MessageQueue:
    """
    Cola de mensajes para evitar saturar el rate limit.

    Implementa un rate limiter simple del lado del cliente.
    """

    def __init__(
        self, max_requests_per_minute: int = 25, max_tokens_per_minute: int = 10000
    ):
        """
        Inicializa la cola.

        Args:
            max_requests_per_minute: Máximo de requests por minuto (con margen)
            max_tokens_per_minute: Máximo de tokens por minuto (con margen)
        """
        self.max_rpm = max_requests_per_minute
        self.max_tpm = max_tokens_per_minute

        self._request_history: List[float] = []
        self._token_history: List[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    def _cleanup_old_entries(self, current_time: float):
        """Limpia entradas más viejas de 1 minuto."""
        one_minute_ago = current_time - 60

        # Limpiar requests
        self._request_history = [
            ts for ts in self._request_history if ts > one_minute_ago
        ]

        # Limpiar tokens
        self._token_history = [
            (ts, tokens) for ts, tokens in self._token_history if ts > one_minute_ago
        ]

    def _get_current_usage(self, current_time: float) -> Dict:
        """Obtiene uso actual en la última ventana de 1 minuto."""
        self._cleanup_old_entries(current_time)

        total_tokens = sum(tokens for _, tokens in self._token_history)

        return {
            "requests": len(self._request_history),
            "tokens": total_tokens,
            "requests_available": self.max_rpm - len(self._request_history),
            "tokens_available": self.max_tpm - total_tokens,
        }

    async def wait_if_needed(self, estimated_tokens: int = 1000) -> Dict:
        """
        Espera si es necesario para no exceder rate limits.

        Args:
            estimated_tokens: Tokens estimados para la próxima request

        Returns:
            Dict con información de uso actual
        """
        async with self._lock:
            current_time = time.time()
            usage = self._get_current_usage(current_time)

            # Verificar si necesitamos esperar
            needs_wait = False
            wait_reason = None

            if usage["requests"] >= self.max_rpm:
                needs_wait = True
                wait_reason = "requests per minute limit"
            elif usage["tokens"] + estimated_tokens > self.max_tpm:
                needs_wait = True
                wait_reason = "tokens per minute limit"

            if needs_wait:
                # Calcular cuánto esperar (hasta que expire la entrada más vieja)
                oldest_entry_time = min(
                    [self._request_history[0]] + [ts for ts, _ in self._token_history]
                    if self._request_history or self._token_history
                    else [current_time]
                )
                wait_time = 60 - (current_time - oldest_entry_time)

                if wait_time > 0:
                    logger.warning(
                        f"⏳ Rate limit approaching ({wait_reason}). "
                        f"Waiting {wait_time:.1f}s before proceeding."
                    )
                    logger.info(
                        f"📊 Current usage: {usage['requests']}/{self.max_rpm} RPM, "
                        f"{usage['tokens']}/{self.max_tpm} TPM"
                    )
                    await asyncio.sleep(wait_time + 0.5)  # +0.5s buffer

                    # Actualizar después de esperar
                    current_time = time.time()
                    usage = self._get_current_usage(current_time)

            # Registrar esta request
            self._request_history.append(current_time)
            self._token_history.append((current_time, estimated_tokens))

            return usage

    async def record_actual_tokens(self, tokens_used: int):
        """
        Actualiza el registro con los tokens reales usados.

        Args:
            tokens_used: Tokens realmente usados (del response)
        """
        async with self._lock:
            # Actualizar la última entrada con tokens reales
            if self._token_history:
                last_ts, estimated = self._token_history[-1]
                self._token_history[-1] = (last_ts, tokens_used)


# Instancia global de la cola (una por proceso)
_global_queues: Dict[str, MessageQueue] = {}


def get_message_queue(provider: str, model: str) -> MessageQueue:
    """
    Obtiene o crea una cola de mensajes para un proveedor/modelo.

    Args:
        provider: Proveedor de IA
        model: Modelo específico

    Returns:
        MessageQueue para ese proveedor/modelo
    """
    key = f"{provider}:{model}"

    if key not in _global_queues:
        # Configurar límites según el proveedor/modelo
        rpm, tpm = _get_rate_limits(provider, model)
        _global_queues[key] = MessageQueue(
            max_requests_per_minute=rpm, max_tokens_per_minute=tpm
        )

    return _global_queues[key]


def _get_rate_limits(provider: str, model: str) -> tuple[int, int]:
    """
    Obtiene los rate limits para un proveedor/modelo.

    Retorna límites con un 20% de margen de seguridad.

    Args:
        provider: Proveedor de IA
        model: Modelo específico

    Returns:
        Tuple (rpm, tpm) con límites seguros
    """
    # Rate limits de Groq (free tier) con 20% de margen
    GROQ_LIMITS = {
        "llama-3.3-70b-versatile": (25, 10000),  # Real: 30 RPM, 12K TPM
        "llama-3.1-8b-instant": (25, 5000),  # Real: 30 RPM, 6K TPM
        "llama-guard-4-12b": (25, 12000),  # Real: 30 RPM, 15K TPM
        "openai/gpt-oss-120b": (25, 6500),  # Real: 30 RPM, 8K TPM
        "openai/gpt-oss-20b": (25, 6500),  # Real: 30 RPM, 8K TPM
        "mixtral-8x7b-32768": (25, 5000),  # Estimado conservador
        "gemma2-9b-it": (25, 5000),  # Estimado conservador
        "qwen/qwen3-32b": (50, 5000),  # Real: 60 RPM, 6K TPM
    }

    if provider == "groq":
        return GROQ_LIMITS.get(model, (25, 5000))  # Default conservador

    # Default para otros proveedores
    return (50, 10000)


async def generate_with_rate_limit_handling(
    generate_func,
    provider: str,
    model: str,
    estimated_tokens: int = 1000,
    enable_queue: bool = True,
    enable_retry: bool = True,
    enable_fallback: bool = True,
) -> Dict:
    """
    Wrapper principal que combina todas las estrategias de rate limit.

    Args:
        generate_func: Función async que genera la respuesta (recibe provider, model)
        provider: Proveedor de IA
        model: Modelo a usar
        estimated_tokens: Tokens estimados para la request
        enable_queue: Si debe usar la cola preventiva
        enable_retry: Si debe reintentar en caso de error
        enable_fallback: Si debe hacer fallback a modelo más barato

    Returns:
        Respuesta del modelo

    Raises:
        RateLimitError: Si falla después de todas las estrategias
    """
    start_time = time.time()

    try:
        # 1. Preventivo: Usar cola para evitar saturar
        if enable_queue:
            queue = get_message_queue(provider, model)
            usage = await queue.wait_if_needed(estimated_tokens)
            logger.debug(
                f"📊 Queue status: {usage['requests']}/{queue.max_rpm} RPM, "
                f"{usage['tokens']}/{queue.max_tpm} TPM"
            )

        # 2. Ejecutar con manejo de reintentos
        if enable_retry:
            result = await RateLimitHandler.execute_with_retry(
                generate_func, provider, model, enable_fallback=enable_fallback
            )
        else:
            result = await generate_func(provider, model)

        # 3. Actualizar cola con tokens reales usados
        if enable_queue and "tokens_used" in result:
            queue = get_message_queue(provider, model)
            await queue.record_actual_tokens(result["tokens_used"])

        elapsed = time.time() - start_time
        logger.info(
            f"✅ Response generated successfully in {elapsed:.2f}s "
            f"using {provider}/{model}"
        )

        return result

    except RateLimitError as e:
        # Error de rate limit después de todos los intentos
        elapsed = time.time() - start_time
        logger.error(f"❌ Rate limit error after {elapsed:.2f}s: {e}", exc_info=False)
        raise

    except Exception as e:
        # Otro tipo de error
        elapsed = time.time() - start_time
        logger.error(f"❌ Unexpected error after {elapsed:.2f}s: {e}", exc_info=True)
        raise


def get_user_friendly_error_message(error: Exception) -> str:
    """
    Convierte un error técnico en un mensaje amigable para el usuario.

    Args:
        error: Excepción capturada

    Returns:
        Mensaje amigable en español
    """
    if isinstance(error, RateLimitError):
        if error.retry_after:
            return (
                f"⏳ El servicio de IA está temporalmente ocupado. "
                f"Por favor intenta de nuevo en {int(error.retry_after)} segundos."
            )
        else:
            return (
                f"⏳ Has alcanzado el límite de uso del modelo {error.model}. "
                f"Por favor espera unos minutos o contacta al administrador para "
                f"aumentar los límites."
            )

    error_str = str(error).lower()

    if "rate_limit" in error_str or "429" in error_str:
        return (
            "⏳ El servicio de IA está temporalmente ocupado debido a alto tráfico. "
            "Intenta de nuevo en unos segundos."
        )

    if "timeout" in error_str:
        return (
            "⏱️ La solicitud tardó demasiado tiempo. "
            "Intenta con un mensaje más corto o espera unos momentos."
        )

    if "api_key" in error_str or "unauthorized" in error_str or "401" in error_str:
        return (
            "🔑 Error de autenticación con el proveedor de IA. "
            "Verifica que tu API key sea válida."
        )

    if "invalid" in error_str and "model" in error_str:
        return (
            "🤖 El modelo de IA configurado no está disponible. "
            "Por favor actualiza la configuración."
        )

    # Error genérico
    return (
        "❌ Ocurrió un error al generar la respuesta. "
        "El equipo técnico ha sido notificado. "
        "Por favor intenta de nuevo en unos momentos."
    )


# Ejemplo de uso:
"""
from app.modules.ai_assistant.rate_limit_handler import generate_with_rate_limit_handling

async def my_generate_function(provider: str, model: str):
    # Tu lógica de generación aquí
    ai_provider = UnifiedAIProvider(provider, model, api_key, ...)
    return await ai_provider.generate_response(messages, system_prompt)

# Usar con rate limit handling
try:
    result = await generate_with_rate_limit_handling(
        generate_func=my_generate_function,
        provider="groq",
        model="llama-3.3-70b-versatile",
        estimated_tokens=1000,
        enable_queue=True,
        enable_retry=True,
        enable_fallback=True,
    )
except RateLimitError as e:
    user_message = get_user_friendly_error_message(e)
    # Mostrar user_message al usuario
"""
