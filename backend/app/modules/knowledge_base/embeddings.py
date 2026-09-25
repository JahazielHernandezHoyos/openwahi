"""
Embeddings generation for knowledge base.

Supports multiple providers:
- sentence-transformers (LOCAL, FREE, RECOMMENDED) - Best for RAG
- jina-ai (API with free tier) - Good quality, 1M tokens/month free
- openai (API, paid) - Highest quality but costs money
- hash-based fallback (for testing only)
"""

import hashlib
import logging
import struct
from typing import List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingsGenerator:
    """
    Generate embeddings using available providers.

    Primary provider: sentence-transformers (local, free, good quality)
    Fallback providers: jina, openai, hash-based

    Example:
        # Use default provider from settings
        gen = EmbeddingsGenerator()
        embedding = await gen.generate_embedding("some text")

        # Override provider
        gen = EmbeddingsGenerator(provider="jina", api_key="your-key")
        embedding = await gen.generate_embedding("some text")
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        api_key: str = None,
    ):
        """
        Initialize embeddings generator.

        Args:
            provider: Embedding provider (sentence-transformers, jina, openai)
            model: Model to use for embeddings
            api_key: API key (for jina/openai)
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.model = model or self._get_default_model()
        self.api_key = api_key
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self._st_model = None  # Lazy load sentence-transformers model

    def _get_default_model(self) -> str:
        """Get default model based on provider."""
        defaults = {
            "sentence-transformers": "multi-qa-MiniLM-L6-cos-v1",  # Best for Q&A/RAG
            "jina": "jina-embeddings-v2-base-en",  # 768 dims
            "openai": "text-embedding-3-small",  # 1536 dims
        }
        return defaults.get(self.provider, settings.EMBEDDING_MODEL)

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If provider is unsupported or configuration is invalid
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, using zero vector")
            return [0.0] * self.dimensions

        if self.provider == "sentence-transformers":
            return await self._generate_sentence_transformer_embedding(text)
        elif self.provider == "jina":
            return await self._generate_jina_embedding(text)
        elif self.provider == "openai":
            return await self._generate_openai_embedding(text)
        else:
            # Fallback to hash-based for testing
            logger.warning(
                f"Unknown provider '{self.provider}', using hash-based fallback. "
                "This is NOT suitable for production!"
            )
            return self._hash_based_embedding(text)

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        This is more efficient than calling generate_embedding() in a loop
        for sentence-transformers provider.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self.provider == "sentence-transformers":
            # Sentence transformers can batch efficiently
            return await self._generate_sentence_transformer_embeddings_batch(texts)
        else:
            # For API-based providers, process one by one
            embeddings = []
            for text in texts:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            return embeddings

    async def _generate_sentence_transformer_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using Sentence Transformers (LOCAL, FREE).

        This is the recommended option for most use cases:
        ✅ 100% free, no API keys needed
        ✅ Runs locally on CPU (fast enough)
        ✅ Good quality for RAG/search
        ✅ ~300MB RAM when loaded
        ✅ Works offline after initial download
        ✅ Model: multi-qa-MiniLM-L6-cos-v1 (optimized for Q&A)

        The model (~80MB) downloads automatically on first use and is cached.
        Location: ~/.cache/torch/sentence_transformers/
        """
        try:
            # Lazy load model (only load once)
            if self._st_model is None:
                from sentence_transformers import SentenceTransformer

                logger.info(f"📦 Loading sentence-transformers model: {self.model}")
                logger.info(
                    "   First time? Model will be downloaded (~80MB). "
                    "This only happens once."
                )

                self._st_model = SentenceTransformer(self.model)

                actual_dims = self._st_model.get_sentence_embedding_dimension()
                logger.info(f"✅ Model loaded: {self.model}")
                logger.info(f"   Dimensions: {actual_dims}")

                # Warn if dimensions mismatch
                if actual_dims != self.dimensions:
                    logger.warning(
                        f"⚠️  Model dimensions ({actual_dims}) don't match "
                        f"EMBEDDING_DIMENSIONS setting ({self.dimensions}). "
                        f"Using model dimensions."
                    )
                    self.dimensions = actual_dims

            # Generate embedding
            import asyncio

            loop = asyncio.get_event_loop()

            # Run in thread pool to not block async event loop
            embedding = await loop.run_in_executor(
                None,
                lambda: self._st_model.encode(text, convert_to_numpy=True).tolist(),
            )

            logger.debug(f"Generated ST embedding with {len(embedding)} dimensions")
            return embedding

        except ImportError:
            logger.error(
                "❌ sentence-transformers not installed. "
                "Install with: uv add sentence-transformers"
            )
            logger.warning(
                "Falling back to hash-based embeddings (NOT RECOMMENDED FOR PRODUCTION)"
            )
            return self._hash_based_embedding(text)

        except Exception as e:
            logger.error(f"Failed to generate sentence-transformer embedding: {e}")
            logger.warning("Falling back to hash-based embeddings")
            return self._hash_based_embedding(text)

    async def _generate_sentence_transformer_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        This is MUCH faster than one-by-one for sentence-transformers.
        Batch encoding can be 5-10x faster depending on batch size.
        """
        try:
            if self._st_model is None:
                from sentence_transformers import SentenceTransformer

                logger.info(f"📦 Loading sentence-transformers model: {self.model}")
                self._st_model = SentenceTransformer(self.model)

                actual_dims = self._st_model.get_sentence_embedding_dimension()
                logger.info(f"✅ Model loaded: {self.model}")

                if actual_dims != self.dimensions:
                    self.dimensions = actual_dims

            import asyncio

            loop = asyncio.get_event_loop()

            # Batch encoding (much faster than one-by-one)
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._st_model.encode(texts, convert_to_numpy=True).tolist(),
            )

            logger.info(f"✅ Generated {len(embeddings)} embeddings in batch")
            return embeddings

        except ImportError:
            logger.error("sentence-transformers not installed, falling back to hash")
            return [self._hash_based_embedding(text) for text in texts]

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            # Fallback to one-by-one hash
            return [self._hash_based_embedding(text) for text in texts]

    async def _generate_jina_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using Jina AI API.

        Jina AI Embeddings v2:
        ✅ FREE tier: 1 million tokens/month (no credit card required)
        ✅ Specialized for RAG and semantic search
        ✅ 768 dimensions (jina-embeddings-v2-base-en)
        ✅ Good quality, better than MiniLM for some tasks
        💵 After free tier: $0.02 per 1M tokens (very cheap)

        Get API key: https://jina.ai/embeddings
        Set JINA_API_KEY in your .env file or pass as api_key parameter.

        Falls back to sentence-transformers if API key is missing.
        """
        try:
            import httpx

            jina_api_key = self.api_key or getattr(settings, "JINA_API_KEY", None)

            if not jina_api_key:
                logger.warning(
                    "No JINA_API_KEY configured, falling back to sentence-transformers"
                )
                return await self._generate_sentence_transformer_embedding(text)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {jina_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": [text],
                        "model": self.model,  # jina-embeddings-v2-base-en
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    logger.debug(
                        f"Generated Jina embedding with {len(embedding)} dimensions"
                    )
                    return embedding
                else:
                    logger.warning(
                        f"Jina API error: {response.status_code} - {response.text[:200]}"
                    )
                    logger.info("Falling back to sentence-transformers")
                    return await self._generate_sentence_transformer_embedding(text)

        except Exception as e:
            logger.warning(f"Error generating Jina embedding: {e}, using fallback")
            return await self._generate_sentence_transformer_embedding(text)

    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI embeddings API.

        OpenAI text-embedding-3-small:
        ✅ Highest quality embeddings
        ✅ 1536 dimensions (configurable)
        ✅ Fast and reliable
        💵 Paid: $0.13 per 1M tokens (more expensive than Jina)

        Get API key: https://platform.openai.com/api-keys
        Set OPENAI_API_KEY in your .env file or pass as api_key parameter.

        Falls back to sentence-transformers if API key is missing.
        """
        try:
            import httpx

            openai_api_key = self.api_key or getattr(settings, "OPENAI_API_KEY", None)

            if not openai_api_key:
                logger.warning(
                    "No OPENAI_API_KEY configured, falling back to sentence-transformers"
                )
                return await self._generate_sentence_transformer_embedding(text)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text,
                        "model": self.model,  # text-embedding-3-small
                        "dimensions": self.dimensions,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]
                    logger.debug(
                        f"Generated OpenAI embedding with {len(embedding)} dimensions"
                    )
                    return embedding
                else:
                    logger.warning(
                        f"OpenAI API error: {response.status_code} - {response.text[:200]}"
                    )
                    logger.info("Falling back to sentence-transformers")
                    return await self._generate_sentence_transformer_embedding(text)

        except Exception as e:
            logger.warning(f"Error generating OpenAI embedding: {e}, using fallback")
            return await self._generate_sentence_transformer_embedding(text)

    def _hash_based_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic pseudo-embedding from text using hashing.

        ⚠️ WARNING: This is NOT suitable for production semantic search!

        This fallback method:
        - Does NOT provide semantic similarity
        - Is deterministic (same text = same vector)
        - Is fast and has no dependencies
        - Should ONLY be used for testing/development

        For production, use:
        1. sentence-transformers (FREE, local, good quality)
        2. jina (FREE tier, API, better quality)
        3. openai (paid, highest quality)
        """
        # Normalize text
        text = text.lower().strip()

        # Generate multiple hash values to fill the embedding dimensions
        embeddings = []
        for i in range(self.dimensions):
            hash_input = f"{text}_{i}".encode()
            hash_value = hashlib.sha256(hash_input).digest()

            # Convert first 4 bytes to float between -1 and 1
            int_value = struct.unpack(">I", hash_value[:4])[0]
            float_value = (int_value / (2**32 - 1)) * 2 - 1
            embeddings.append(float_value)

        # Normalize the vector (unit length)
        magnitude = sum(x**2 for x in embeddings) ** 0.5
        if magnitude > 0:
            embeddings = [x / magnitude for x in embeddings]

        return embeddings


# Factory function
def get_embeddings_generator(
    provider: str = None,
    model: str = None,
    api_key: str = None,
) -> EmbeddingsGenerator:
    """
    Get an embeddings generator instance.

    This is the recommended way to get an embeddings generator.
    Uses settings from environment by default, but can be overridden.

    Args:
        provider: Override default provider (sentence-transformers, jina, openai)
        model: Override default model
        api_key: API key for jina/openai (if using those providers)

    Returns:
        EmbeddingsGenerator instance

    Example:
        # Use defaults from settings
        gen = get_embeddings_generator()
        embedding = await gen.generate_embedding("hello world")

        # Override provider
        gen = get_embeddings_generator(provider="jina", api_key="your-key")
        embedding = await gen.generate_embedding("hello world")

        # Batch processing (faster for sentence-transformers)
        texts = ["text 1", "text 2", "text 3"]
        embeddings = await gen.generate_embeddings(texts)
    """
    return EmbeddingsGenerator(provider=provider, model=model, api_key=api_key)
