"""
Unified AI provider using LangChain.
Simple to use, just change provider and API key.
"""

import json
import logging
import os
from typing import Dict, List, Optional

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

LLAMACPP_DEFAULT_MODEL = "Qwen3.5-0.8B-Q8_0"
LLAMACPP_DEFAULT_BASE_URL = "http://llamacpp:8080/v1"


# ---------------------------------------------------------------------------
# Bedrock native response → OpenAI format converter
# ---------------------------------------------------------------------------
# Bedrock con JumpCube bearer token devuelve formato nativo Bedrock Converse:
#   { "Output": { "message": { "content": [{"text": "..."}] } }, "Version": "...",
#     "choices": null, ... }
# LangChain ChatOpenAI espera choices[0].message.content — explota con null.
# Interceptamos la respuesta antes del parser con un httpx transport custom.

class _BedrockToOpenAITransport(httpx.BaseTransport):
    """
    httpx transport que convierte respuestas nativas Bedrock Converse
    al formato OpenAI estándar que ChatOpenAI puede parsear.
    """

    def __init__(self, wrapped: httpx.BaseTransport):
        self._wrapped = wrapped

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._wrapped.handle_request(request)
        response.read()  # forzar lectura completa antes de acceder a .content
        return self._patch_response(response)

    def _patch_response(self, response: httpx.Response) -> httpx.Response:
        if response.status_code != 200:
            return response
        try:
            body = json.loads(response.content)
            # Solo convertir si choices es null y hay Output nativo Bedrock
            if body.get("choices") is None and "Output" in body:
                content_blocks = (
                    body.get("Output", {})
                    .get("message", {})
                    .get("content", [])
                )
                text = " ".join(
                    b.get("text", "") for b in content_blocks if "text" in b
                )
                usage = body.get("usage", {})
                patched = {
                    "id": body.get("id", "bedrock-native"),
                    "object": "chat.completion",
                    "created": body.get("created", 0),
                    "model": body.get("model", ""),
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": text},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": usage.get("inputTokens", usage.get("prompt_tokens", 0)),
                        "completion_tokens": usage.get("outputTokens", usage.get("completion_tokens", 0)),
                        "total_tokens": usage.get("totalTokens", usage.get("total_tokens", 0)),
                    },
                }
                new_content = json.dumps(patched).encode()
                return httpx.Response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=new_content,
                )
        except Exception as e:
            logger.warning(f"⚠️ BedrockToOpenAITransport patch failed: {e}")
        return response


class _AsyncBedrockToOpenAITransport(httpx.AsyncBaseTransport):
    """Versión async del transport Bedrock→OpenAI."""

    def __init__(self, wrapped: httpx.AsyncBaseTransport):
        self._wrapped = wrapped

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._wrapped.handle_async_request(request)
        await response.aread()  # forzar lectura completa antes de acceder a .content
        return self._patch_response(response)

    def _patch_response(self, response: httpx.Response) -> httpx.Response:
        if response.status_code != 200:
            return response
        try:
            body = json.loads(response.content)
            if body.get("choices") is None and "Output" in body:
                content_blocks = (
                    body.get("Output", {})
                    .get("message", {})
                    .get("content", [])
                )
                text = " ".join(
                    b.get("text", "") for b in content_blocks if "text" in b
                )
                usage = body.get("usage", {})
                patched = {
                    "id": body.get("id", "bedrock-native"),
                    "object": "chat.completion",
                    "created": body.get("created", 0),
                    "model": body.get("model", ""),
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": text},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": usage.get("inputTokens", usage.get("prompt_tokens", 0)),
                        "completion_tokens": usage.get("outputTokens", usage.get("completion_tokens", 0)),
                        "total_tokens": usage.get("totalTokens", usage.get("total_tokens", 0)),
                    },
                }
                new_content = json.dumps(patched).encode()
                return httpx.Response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=new_content,
                )
        except Exception as e:
            logger.warning(f"⚠️ AsyncBedrockToOpenAITransport patch failed: {e}")
        return response


class UnifiedAIProvider:
    """
    Proveedor unificado usando LangChain.
    Soporta: Groq, OpenAI, Anthropic
    """

    PROVIDERS = {
        "groq": {
            "class": ChatGroq,
            "models": [
                # Production models (recomendados)
                "llama-3.3-70b-versatile",  # Reemplazo de llama-3.1-70b
                "llama-3.1-8b-instant",
                "llama-guard-4-12b",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                # Preview models
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
                "qwen/qwen3-32b",
            ],
        },
        # Puedes agregar más proveedores aquí cuando instales sus paquetes:
        # "openai": {
        #     "class": ChatOpenAI,
        #     "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        # },
        # "anthropic": {
        #     "class": ChatAnthropic,
        #     "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        # },
        "bedrock": {
            "class": ChatOpenAI,  # usa cliente OpenAI-compatible
            "models": [
                "amazon.nova-lite-v1:0",
                "amazon.nova-micro-v1:0",
                "amazon.nova-pro-v1:0",
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
            ],
            "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com/",
        },
        "llamacpp": {
            "class": ChatOpenAI,
            "models": [LLAMACPP_DEFAULT_MODEL],
        },
        "openai_compatible": {
            "class": ChatOpenAI,
            # The model and endpoint are supplied by each managed-chain entry.
            "models": [],
        },
    }

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        base_url: Optional[str] = None,
    ):
        """
        Inicializa el proveedor.

        Args:
            provider: Nombre del proveedor ('groq', 'openai', 'anthropic')
            model: Nombre del modelo
            api_key: API key del proveedor (optional for local llama.cpp)
            temperature: Temperatura para generación (0.0 - 1.0)
            max_tokens: Máximo de tokens a generar
        """

        if provider not in self.PROVIDERS:
            raise ValueError(
                f"Provider '{provider}' not supported. "
                f"Available providers: {list(self.PROVIDERS.keys())}"
            )

        provider_class = self.PROVIDERS[provider]["class"]

        try:
            # Generic OpenAI-compatible entries receive their endpoint at runtime.
            provider_config = self.PROVIDERS[provider]
            configured_base_url = provider_config.get("base_url")
            if provider != "openai_compatible":
                base_url = configured_base_url
            elif not base_url:
                raise ValueError("base_url is required for openai_compatible providers")
            if provider == "llamacpp":
                base_url = os.getenv("LLAMACPP_BASE_URL", LLAMACPP_DEFAULT_BASE_URL)
                api_key = "local-no-key"

            kwargs = {
                "model": model,
                "api_key": api_key,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if base_url:
                kwargs["base_url"] = base_url
            if provider == "llamacpp":
                # Qwen3.5 can otherwise spend the whole token budget on hidden reasoning.
                kwargs["extra_body"] = {
                    "chat_template_kwargs": {"enable_thinking": False}
                }

            # Bedrock via JumpCube devuelve formato nativo Converse (choices=null, Output=...).
            # Inyectamos transports custom que lo convierten a OpenAI estándar en tiempo real.
            if provider == "bedrock":
                kwargs["http_client"] = httpx.Client(
                    transport=_BedrockToOpenAITransport(httpx.HTTPTransport()),
                )
                kwargs["http_async_client"] = httpx.AsyncClient(
                    transport=_AsyncBedrockToOpenAITransport(httpx.AsyncHTTPTransport()),
                )

            # LangChain hace todo el trabajo pesado
            self.llm = provider_class(**kwargs)

            self.provider = provider
            self.model = model
            logger.info(f"Initialized AI provider: {provider} with model: {model}")

        except Exception as e:
            logger.error(f"Failed to initialize provider {provider}: {e}")
            raise

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Genera respuesta. Compatible con cualquier proveedor.

        Args:
            messages: Lista de mensajes [{"role": "user/assistant", "content": "..."}]
            system_prompt: Prompt del sistema (opcional)

        Returns:
            {
                "content": str,
                "tokens_used": int,
                "model": str,
                "provider": str,
            }
        """

        try:
            # Convertir a formato LangChain
            lc_messages = []

            # Agregar system prompt si existe
            if system_prompt:
                lc_messages.append(SystemMessage(content=system_prompt))

            # Convertir mensajes a formato LangChain
            for msg in messages:
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))

            # Invocar el modelo (funciona igual para todos los proveedores!)
            response = await self.llm.ainvoke(lc_messages)

            # Extraer información de uso de tokens
            tokens_used = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens", 0)

            return {
                "content": response.content,
                "tokens_used": tokens_used,
                "model": self.model,
                "provider": self.provider,
            }

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise

    def generate_response_sync(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> Dict:
        """
        Versión síncrona de generate_response.
        Útil para casos donde no se puede usar async.
        """
        try:
            # Convertir a formato LangChain
            lc_messages = []

            if system_prompt:
                lc_messages.append(SystemMessage(content=system_prompt))

            for msg in messages:
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))

            # Invocar de forma síncrona
            response = self.llm.invoke(lc_messages)

            # Extraer tokens
            tokens_used = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = response.usage_metadata.get("total_tokens", 0)

            return {
                "content": response.content,
                "tokens_used": tokens_used,
                "model": self.model,
                "provider": self.provider,
            }

        except Exception as e:
            logger.error(f"Error generating AI response (sync): {e}")
            raise

    @classmethod
    def get_available_models(cls, provider: str) -> List[str]:
        """
        Obtiene modelos disponibles para un proveedor.

        Args:
            provider: Nombre del proveedor

        Returns:
            Lista de modelos disponibles
        """
        if provider not in cls.PROVIDERS:
            return []
        if provider == "llamacpp":
            return [os.getenv("LLAMACPP_MODEL", LLAMACPP_DEFAULT_MODEL)]
        if provider == "openai_compatible":
            return []
        return cls.PROVIDERS[provider]["models"]

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Obtiene lista de proveedores disponibles.

        Returns:
            Lista de nombres de proveedores
        """
        return list(cls.PROVIDERS.keys())

    def get_llm(self):
        """
        Get the underlying LLM instance.

        Returns:
            The LangChain LLM instance
        """
        return self.llm

    @classmethod
    def validate_provider_model(cls, provider: str, model: str) -> bool:
        """
        Valida si un modelo es válido para un proveedor.

        Args:
            provider: Nombre del proveedor
            model: Nombre del modelo

        Returns:
            True si el modelo es válido para el proveedor
        """
        if provider not in cls.PROVIDERS:
            return False

        if provider == "openai_compatible":
            return bool(model and model.strip())

        available_models = cls.get_available_models(provider)
        return model in available_models
