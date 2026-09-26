"""
AI Assistant Service - Business logic for AI-powered WhatsApp responses.
"""

import io
import logging
import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .encryption import decrypt_api_key, encrypt_api_key
from .memory import ConversationMemory
from .models import (
    WhatsAppAIConfigDB,
    WhatsAppAIConversationDB,
    WhatsAppAIMessageDB,
)
from .prompt_enhancer import PromptEnhancer
from .provider import UnifiedAIProvider
from .rate_limit_handler import (
    RateLimitError,
    generate_with_rate_limit_handling,
    get_user_friendly_error_message,
)

logger = logging.getLogger(__name__)

# Audio message types sent by WhatsApp / GOWA
AUDIO_MESSAGE_TYPES = {"audio", "ptt", "voice"}

# Non-secret storage value for local providers that do not use credentials.
_KEYLESS_LOCAL_API_KEY_SENTINEL = "__openwahi_keyless_local_provider__"


def _api_key_for_storage(provider: str, api_key: Optional[str]) -> str:
    """Return a non-empty value for encryption without relaxing remote-key checks."""
    if provider == "llamacpp":
        return _KEYLESS_LOCAL_API_KEY_SENTINEL
    if not api_key:
        raise ValueError("API key is required for remote AI providers")
    return api_key


async def transcribe_audio_via_service(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
) -> Optional[str]:
    """
    Transcribe audio usando el microservicio de transcripción (transcriber/).

    Setting: TRANSCRIBER_URL (default: http://localhost:8001)
    Si el microservicio no está disponible, retorna None para que el caller
    pueda hacer fallback a la lógica anterior.
    """
    import httpx

    from app.config.settings import settings

    transcriber_url = settings.TRANSCRIBER_URL

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{transcriber_url}/transcribe",
                files={"audio": (filename, audio_bytes, "audio/ogg")},
                data={"filename": filename},
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("text", "").strip()
            source = data.get("source", "unknown")
            duration_ms = data.get("duration_ms", 0)

            if text:
                logger.info(
                    f"Audio transcribed via {source} ({duration_ms}ms, {len(audio_bytes)} bytes → {len(text)} chars)"
                )
                return text
            else:
                logger.warning("Transcriber service returned empty text")
                return None

    except httpx.ConnectError:
        logger.warning(
            f"Transcriber service not available at {transcriber_url}, falling back to direct transcription"
        )
        return None
    except Exception as e:
        logger.error(f"Error calling transcriber service: {e}", exc_info=True)
        return None


async def transcribe_audio(
    audio_bytes: bytes,
    api_key: str,
    provider: str = "groq",
    filename: str = "audio.ogg",
) -> Optional[str]:
    """
    Transcribe audio bytes using Groq Whisper with the user's own API key.

    Args:
        audio_bytes: Raw audio bytes (ogg/opus from WhatsApp)
        api_key: Decrypted user API key (Groq token)
        provider: AI provider (currently only 'groq' supports Whisper)
        filename: Filename hint so the API detects the format (default: audio.ogg)

    Returns:
        Transcribed text or None if transcription is unavailable/failed
    """
    # Si el proveedor no es groq pero hay GROQ_API_KEY global, usarla para transcripción
    import os
    if provider != "groq":
        fallback_key = os.getenv("GROQ_API_KEY")
        if fallback_key:
            logger.info(
                f"Provider '{provider}' doesn't support audio — using global GROQ_API_KEY for transcription"
            )
            api_key = fallback_key
        else:
            logger.warning(
                f"Audio transcription not supported for provider '{provider}' and no GROQ_API_KEY available, skipping"
            )
            return None

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename  # Groq uses the filename to detect the format

        transcription = await client.audio.transcriptions.create(
            file=(filename, audio_file),
            model="whisper-large-v3-turbo",
            response_format="text",
        )

        # Groq returns a plain string when response_format="text"
        text = (
            transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
        )
        text = text.strip()

        if text:
            logger.info(
                f"Audio transcribed successfully ({len(audio_bytes)} bytes → {len(text)} chars)"
            )
        else:
            logger.warning("Transcription returned empty text")

        return text or None

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        return None

async def _get_rag_context(
    db: AsyncSession,
    config: WhatsAppAIConfigDB,
    message_text: str,
) -> str:
    """
    Get RAG context from knowledge bases (simple approach).

    Args:
        db: Database session
        config: AI configuration with RAG settings
        message_text: User message to search for

    Returns:
        RAG context string to append to system prompt
    """
    if not config.use_knowledge_base or not config.knowledge_bases:
        return ""

    try:
        from app.modules.knowledge_base.service import KnowledgeBaseService

        from .encryption import decrypt_api_key

        # Extract KB IDs from relationship
        kb_ids = [kb.id for kb in config.knowledge_bases]

        if not kb_ids:
            return ""

        # Get user's API key for embeddings
        user_api_key = decrypt_api_key(config.api_key_encrypted)

        # Search knowledge bases using user's API key for embeddings
        results = await KnowledgeBaseService.search(
            db=db,
            knowledge_base_ids=kb_ids,
            query=message_text,
            top_k=config.rag_top_k,
            min_score=config.rag_min_score,
            api_key=user_api_key,
        )

        if not results:
            return ""

        # Build context string
        context_parts = ["\n\n### Información relevante de tu base de conocimientos:\n"]

        for i, result in enumerate(results, 1):
            context_parts.append(
                f"{i}. {result.content}\n"
                f"   (Fuente: {result.document_name}, Relevancia: {result.score:.2f})\n"
            )

        context_parts.append(
            "\nUsa esta información para responder de manera precisa. "
            "Si la información no es relevante para la pregunta, ignórala."
        )

        logger.info(f"RAG context added: {len(results)} results for query '{message_text[:50]}...'")

        return "\n".join(context_parts)

    except Exception as e:
        logger.error(f"Error getting RAG context: {e}", exc_info=True)
        return ""


async def _get_agentic_rag_context(
    db: AsyncSession,
    config: WhatsAppAIConfigDB,
    message_text: str,
) -> str:
    """
    Get RAG context using agentic approach with LangGraph.

    This function uses an intelligent agent that can:
    - Make MULTIPLE strategic queries to the SAME knowledge base
    - Compare information across different chunks (e.g., prices, features)
    - Gather related information scattered across the knowledge base
    - Synthesize information while respecting the system prompt

    The agent works with ONE knowledge base at a time but makes intelligent
    multiple searches within it.

    Args:
        db: Database session
        config: AI configuration with RAG settings
        message_text: User message to search for

    Returns:
        RAG context string to append to system prompt
    """
    logger.info(f"🔍 RAG Check - use_knowledge_base: {config.use_knowledge_base}")

    if not config.use_knowledge_base:
        logger.warning("⚠️ RAG is DISABLED for this config")
        return ""

    if not config.knowledge_bases:
        logger.warning("⚠️ NO knowledge bases associated with this config")
        return ""

    try:
        from app.modules.rag_agent.agent import create_rag_agent

        from .encryption import decrypt_api_key

        # Use the first KB - agent will make multiple queries within it
        kb = config.knowledge_bases[0]
        kb_id = kb.id
        kb_name = getattr(kb, "name", "Base de Conocimientos")

        logger.info(f"📚 Using Knowledge Base: {kb_name} (ID: {kb_id})")

        # Get user's API key for embeddings
        user_api_key = decrypt_api_key(config.api_key_encrypted)

        # Get system prompt to pass to agent - CRITICAL: Add strict instruction
        system_prompt = config.system_prompt or "Eres un asistente útil."

        # ADD STRICT INSTRUCTION TO NOT HALLUCINATE
        system_prompt += """

🚨 INSTRUCCIÓN CRÍTICA:
- SOLO puedes responder basándote en la información de la base de conocimientos
- SI NO ENCUENTRAS información relevante, debes decir "No tengo esa información en mi base de datos"
- NUNCA inventes precios, productos o características que no estén en los documentos
- Si el usuario pregunta por algo que no existe, indícalo claramente
- SIEMPRE menciona las fuentes de donde sacas la información
"""

        logger.info(f"🤖 Creating agent with system prompt: {system_prompt[:100]}...")

        # Create LLM for agent
        llm = UnifiedAIProvider(
            provider=config.provider,
            model=config.model,
            api_key=user_api_key,
            temperature=0.1,  # Very low temperature to avoid hallucination
            max_tokens=2000,
        ).get_llm()

        # Create RAG agent for this specific KB
        agent = create_rag_agent(
            db=db,
            llm=llm,
            api_key=user_api_key,
            knowledge_base_id=kb_id,
            knowledge_base_name=kb_name,
            system_prompt=system_prompt,
            max_iterations=3,  # Allow up to 3 search iterations
            top_k=config.rag_top_k,
            min_score=config.rag_min_score,
        )

        # Query the agent - it will make multiple strategic searches
        logger.info(f"🔎 Starting agentic RAG search for: '{message_text[:100]}...'")

        result = await agent.query(query=message_text)

        # Log detailed results
        logger.info("📊 Agent Results:")
        logger.info(f"  - Queries executed: {len(result.get('queries_executed', []))}")
        logger.info(f"  - Results found: {len(result.get('results', []))}")
        logger.info(f"  - Errors: {len(result.get('errors', []))}")

        if result.get("queries_executed"):
            logger.info(f"  - Queries: {result['queries_executed']}")

        # Check if we got results
        if not result.get("results") or len(result["results"]) == 0:
            logger.warning("⚠️ Agentic RAG found NO relevant results")
            logger.warning(f"   Query was: {message_text}")

            # Return a strict instruction to not hallucinate
            return """

### ⚠️ INFORMACIÓN IMPORTANTE:
NO se encontró información relevante en la base de conocimientos para esta consulta.

DEBES responder:
"Lo siento, no tengo información sobre eso en mi base de datos actual. ¿Puedo ayudarte con algo más?"

NO inventes información. NO uses tu conocimiento general.
"""

        # Get the number of queries executed
        num_queries = len(result.get("queries_executed", []))

        # Use the combined context from the agent
        context = result.get("context", "")

        if context:
            logger.info(
                f"✅ Agentic RAG SUCCESS: {num_queries} queries, "
                f"{len(result['results'])} results found"
            )

            # Add clear instruction to use ONLY this information
            strict_context = f"""

### 📚 INFORMACIÓN DE LA BASE DE CONOCIMIENTOS:

{context}

### 🚨 INSTRUCCIONES OBLIGATORIAS:
1. USA SOLAMENTE la información proporcionada arriba
2. Si la pregunta requiere información que NO está arriba, di "No tengo esa información"
3. NO inventes precios, productos o datos que no aparezcan arriba
4. Menciona las fuentes cuando cites información
5. Si algo no está claro en la información, indícalo
"""

            return strict_context

        logger.warning("⚠️ Agent returned no context despite having results")
        return ""

    except Exception as e:
        logger.error(f"❌ Error getting agentic RAG context: {e}", exc_info=True)
        logger.error(f"   Exception type: {type(e).__name__}")
        logger.error(f"   Exception args: {e.args}")

        # Fallback to simple RAG if agentic approach fails
        logger.info("🔄 Falling back to simple RAG approach")
        return await _get_rag_context(db, config, message_text)


class AIAssistantService:
    """Servicio para gestionar asistentes de IA en WhatsApp."""

    @staticmethod
    async def get_config_by_phone(
        db: AsyncSession,
        device_id: UUID,
        phone_number: str,
    ) -> Optional[WhatsAppAIConfigDB]:
        """
        Obtiene configuración de IA para un número específico en un dispositivo.

        Args:
            db: Sesión de base de datos
            device_id: ID del dispositivo
            phone_number: Número de teléfono configurado

        Returns:
            Configuración de IA o None si no existe
        """
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(
                WhatsAppAIConfigDB.device_id == device_id,
                WhatsAppAIConfigDB.phone_number == phone_number,
            )
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_config(
        db: AsyncSession,
        config_id: UUID,
    ) -> Optional[WhatsAppAIConfigDB]:
        """Obtiene configuración de IA por ID."""
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.id == config_id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_configs(
        db: AsyncSession,
        device_id: UUID,
    ) -> list[WhatsAppAIConfigDB]:
        """Lista todas las configuraciones de IA para un dispositivo."""
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.device_id == device_id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_configs_by_user(
        db: AsyncSession,
        user_id: str,
    ) -> list[WhatsAppAIConfigDB]:
        """Lista todas las configs del usuario (con o sin device)."""
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.user_id == user_id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
            .order_by(WhatsAppAIConfigDB.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_config(
        db: AsyncSession,
        user_id: str,
        provider: str,
        model: str,
        api_key: Optional[str],
        device_id: Optional[UUID] = None,
        phone_number: Optional[str] = None,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_memory: bool = True,
        memory_window: int = 10,
        auto_enhance_prompt: bool = True,
        use_knowledge_base: bool = False,
        knowledge_base_ids: Optional[List[UUID]] = None,
        rag_top_k: int = 3,
        rag_min_score: float = 0.75,
    ) -> WhatsAppAIConfigDB:
        """
        Crea una nueva configuración de IA.

        Args:
            db: Sesión de base de datos
            device_id: ID del dispositivo
            user_id: ID del usuario
            phone_number: Número de teléfono para activar el bot
            provider: Proveedor de IA
            model: Modelo a usar
            api_key: API key del proveedor (será encriptada)
            system_prompt: Prompt del sistema
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens
            use_memory: Si usar memoria de conversación
            memory_window: Ventana de memoria
            auto_enhance_prompt: Si mejorar el prompt automáticamente
            use_knowledge_base: Si usar RAG con knowledge bases
            knowledge_base_ids: Lista de IDs de knowledge bases
            rag_top_k: Número de chunks a recuperar
            rag_min_score: Score mínimo de similitud

        Returns:
            Configuración creada
        """
        from app.modules.knowledge_base.models import KnowledgeBaseDB

        # Keep the existing NOT NULL/encrypted column compatible for keyless local inference.
        encrypted_key = encrypt_api_key(_api_key_for_storage(provider, api_key))

        config = WhatsAppAIConfigDB(
            device_id=device_id,
            user_id=user_id,
            phone_number=phone_number,
            name=name,
            provider=provider,
            model=model,
            api_key_encrypted=encrypted_key,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_memory=use_memory,
            memory_window=memory_window,
            auto_enhance_prompt=auto_enhance_prompt,
            use_knowledge_base=use_knowledge_base,
            rag_top_k=rag_top_k,
            rag_min_score=rag_min_score,
            is_enabled=False,  # Por defecto deshabilitado
        )

        db.add(config)
        await db.commit()
        await db.refresh(config)

        # Add knowledge base relationships if provided
        if knowledge_base_ids:
            from .models import AIConfigKnowledgeBase

            # Create relationship records directly to avoid lazy loading issues
            for kb_id in knowledge_base_ids:
                relationship = AIConfigKnowledgeBase(
                    ai_config_id=config.id,
                    knowledge_base_id=kb_id,
                )
                db.add(relationship)

            await db.commit()

        # Reload config with relationships loaded for response serialization
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.id == config.id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        config = result.scalar_one()

        logger.info(f"Created AI config for device {device_id}, phone {phone_number}")

        return config

    @staticmethod
    async def update_config(
        db: AsyncSession,
        config_id: UUID,
        **updates,
    ) -> Optional[WhatsAppAIConfigDB]:
        """
        Actualiza una configuración de IA.

        Args:
            db: Sesión de base de datos
            config_id: ID de la configuración
            **updates: Campos a actualizar

        Returns:
            Configuración actualizada o None si no existe
        """
        config = await AIAssistantService.get_config(db, config_id)

        if not config:
            return None

        from app.modules.knowledge_base.models import KnowledgeBaseDB

        target_provider = updates.get("provider", config.provider)
        provider_changed = "provider" in updates and target_provider != config.provider

        # Re-encrypt explicit key changes and replace obsolete remote keys when moving local.
        if "api_key" in updates or provider_changed:
            api_key = updates.pop("api_key", None)
            updates["api_key_encrypted"] = encrypt_api_key(
                _api_key_for_storage(target_provider, api_key)
            )

        # Manejar knowledge_base_ids por separado (many-to-many relationship)
        kb_ids_to_set = None
        if "knowledge_base_ids" in updates:
            kb_ids_to_set = updates.pop("knowledge_base_ids")

        # Actualizar campos simples
        for key, value in updates.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)

        await db.commit()

        # Actualizar relaciones de knowledge bases si se proporcionaron
        if kb_ids_to_set is not None:
            from .models import AIConfigKnowledgeBase

            # Delete existing relationships
            await db.execute(
                delete(AIConfigKnowledgeBase).where(AIConfigKnowledgeBase.ai_config_id == config_id)
            )

            # Create new relationships
            if kb_ids_to_set:
                for kb_id in kb_ids_to_set:
                    relationship = AIConfigKnowledgeBase(
                        ai_config_id=config_id,
                        knowledge_base_id=kb_id,
                    )
                    db.add(relationship)

            await db.commit()

        # Reload config with relationships loaded for response serialization
        result = await db.execute(
            select(WhatsAppAIConfigDB)
            .where(WhatsAppAIConfigDB.id == config_id)
            .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
        )
        config = result.scalar_one()

        logger.info(f"Updated AI config {config_id}")

        return config

    @staticmethod
    async def delete_config(
        db: AsyncSession,
        config_id: UUID,
    ) -> bool:
        """Elimina una configuración de IA."""
        config = await AIAssistantService.get_config(db, config_id)

        if not config:
            return False

        await db.delete(config)
        await db.commit()

        logger.info(f"Deleted AI config {config_id}")

        return True

    @staticmethod
    async def toggle_config(
        db: AsyncSession,
        config_id: UUID,
        enabled: bool,
    ) -> Optional[WhatsAppAIConfigDB]:
        """Activa o desactiva una configuración."""
        return await AIAssistantService.update_config(db, config_id, is_enabled=enabled)

    @staticmethod
    async def process_incoming_message(
        db: AsyncSession,
        device_id: UUID,
        from_phone: str,
        message_text: str,
        message_id: Optional[UUID] = None,
    ) -> Optional[str]:
        """
        Procesa un mensaje entrante y genera respuesta con IA si está configurado.

        Args:
            db: Sesión de base de datos
            device_id: ID del dispositivo que recibe el mensaje
            from_phone: Número de teléfono del remitente
            message_text: Contenido del mensaje
            message_id: ID del mensaje de WhatsApp

        Returns:
            Respuesta generada o None si no debe responder
        """
        start_time = time.time()

        try:
            # 1. Buscar configuración activa para este dispositivo
            # El bot responde a CUALQUIER número que le escriba
            result = await db.execute(
                select(WhatsAppAIConfigDB)
                .where(
                    WhatsAppAIConfigDB.device_id == device_id,
                    WhatsAppAIConfigDB.is_enabled == True,
                )
                .options(selectinload(WhatsAppAIConfigDB.knowledge_bases))
            )
            config = result.scalar_one_or_none()

            if not config:
                logger.debug(f"No active AI config for device {device_id}")
                return None

            logger.info(f"Processing message from {from_phone} with AI config {config.id}")

            # 3. Obtener o crear conversación
            conversation = await AIAssistantService._get_or_create_conversation(
                db, config.id, from_phone
            )

            # 4. Guardar mensaje del usuario
            await ConversationMemory.save_message(
                db=db,
                conversation_id=conversation.id,
                role="user",
                content=message_text,
                whatsapp_message_id=message_id,
            )

            # 5. Construir contexto si está habilitado
            context_messages = []
            if config.use_memory:
                context_messages = await ConversationMemory.build_context(
                    db, conversation.id, config.memory_window
                )
            else:
                # Sin memoria, solo el mensaje actual
                context_messages = [{"role": "user", "content": message_text}]

            # 6. Preparar system prompt
            system_prompt = config.system_prompt or ""
            if config.auto_enhance_prompt:
                system_prompt = PromptEnhancer.enhance_prompt(system_prompt)

            # 6.5. Add RAG context if enabled (using agentic approach)
            logger.info(f"💬 Processing message: '{message_text[:50]}...'")
            logger.info(f"🎯 Config ID: {config.id}, Device: {device_id}")

            rag_context = await _get_agentic_rag_context(db, config, message_text)

            if rag_context:
                logger.info(f"✅ RAG context added to system prompt ({len(rag_context)} chars)")
                system_prompt += rag_context
            else:
                logger.warning(f"⚠️ NO RAG context returned for message: '{message_text[:50]}'")

                # If RAG is enabled but returned nothing, add strict warning
                if config.use_knowledge_base and config.knowledge_bases:
                    system_prompt += """

⚠️ ADVERTENCIA: No se encontró información en la base de conocimientos.
Debes informar al usuario que no tienes esa información en tu base de datos.
NO inventes información.
"""

            # 7. Determinar si usuario es Pro y elegir key/proveedor
            from app.modules.subscriptions.service import get_or_create_subscription

            from .usage_tracker import check_conversation_limit

            subscription = await get_or_create_subscription(db, config.user_id)
            user_plan = subscription.plan
            is_managed = (user_plan.value == "pro")

            if is_managed:
                # Plan Pro: verificar límite mensual primero
                from app.config.settings import settings as app_settings
                allowed, remaining = await check_conversation_limit(db, config.user_id, user_plan)
                if not allowed:
                    logger.warning(
                        f"🚫 User {config.user_id} hit Pro monthly limit — blocking message"
                    )
                    return (
                        "Has alcanzado el límite de 3,000 conversaciones de tu plan Pro este mes. "
                        "Tu límite se renueva el 1° del próximo mes. "
                        "Para más conversaciones, contacta soporte."
                    )

                # Usar la managed key de la plataforma
                api_key = app_settings.BEDROCK_API_KEY or ""
                effective_provider = app_settings.MANAGED_AI_PROVIDER
                effective_model = app_settings.MANAGED_AI_MODEL
                logger.info(
                    f"🔑 Plan Pro: using managed key for user {config.user_id} "
                    f"({remaining} conversations remaining this month)"
                )
            else:
                # Free/Enterprise: usar key del usuario
                api_key = decrypt_api_key(config.api_key_encrypted)
                effective_provider = config.provider
                effective_model = config.model

            # Verificar si debe usar agente LangGraph
            use_agent = getattr(config, "use_agent", False)

            if use_agent:
                # Usar LangGraph agent con herramientas dinámicas
                logger.info("🤖 Using LangGraph agent with dynamic tools")

                from .langgraph_agent import process_message_with_agent

                # Resolve the DB-managed chain for Plan Pro tool runs. An empty
                # table deliberately preserves the legacy env-based escalation.
                chain_choices = []
                if is_managed:
                    from .provider_chain import (
                        chain_exists,
                        get_chain_choices,
                        record_chain_failure,
                        record_chain_success,
                        resolve_chain_provider,
                    )
                    from .tool_loader import DynamicToolLoader

                    tool_count = await DynamicToolLoader.count_enabled_tools(
                        db, config.user_id
                    )
                    chain_active = await chain_exists(db)
                    choice = await resolve_chain_provider(
                        db,
                        tool_count=tool_count,
                        chat_provider=str(effective_provider),
                        chat_model=str(effective_model),
                        chat_api_key=api_key,
                    )
                    if chain_active and choice.entry_id is not None:
                        chain_choices = await get_chain_choices(
                            db,
                            tool_count=tool_count,
                            chat_provider=str(effective_provider),
                            chat_model=str(effective_model),
                            chat_api_key=api_key,
                        )
                    else:
                        chain_choices = [choice]
                    logger.info(f"🔗 Chain: {choice.reason}")
                else:
                    choice = None

                # A managed chain gets the initial attempt plus at most two
                # failovers. User-key and legacy flows remain single-attempt.
                attempts = chain_choices[:3] if chain_choices else [None]
                last_error = None
                for attempt_index, chain_choice in enumerate(attempts):
                    if chain_choice is not None:
                        effective_provider = chain_choice.provider
                        effective_model = chain_choice.model
                        api_key = chain_choice.api_key
                        usage_provider = chain_choice.provider_name or chain_choice.provider
                        base_url = chain_choice.base_url
                    else:
                        usage_provider = str(effective_provider)
                        base_url = None

                    if attempt_index:
                        logger.info(
                            f"🔁 Chain fallback {attempt_index}: "
                            f"{usage_provider}/{effective_model}"
                        )
                    attempt_started = time.perf_counter()
                    try:
                        provider_instance = UnifiedAIProvider(
                            provider=effective_provider,
                            model=effective_model,
                            api_key=api_key,
                            temperature=config.temperature,
                            max_tokens=config.max_tokens,
                            base_url=base_url,
                        )
                        llm = provider_instance.get_llm()
                        response_content = await process_message_with_agent(
                            db=db,
                            user_id=config.user_id,
                            llm=llm,
                            system_prompt=system_prompt,
                            message_text=message_text,
                            provider=usage_provider,
                            model=effective_model,
                            is_managed=is_managed,
                            config_id=config.id,
                            conversation_id=conversation.id,
                        )
                        if chain_choice is not None and chain_choice.entry_id is not None:
                            latency_ms = int((time.perf_counter() - attempt_started) * 1000)
                            await record_chain_success(db, chain_choice.entry_id, latency_ms)
                        break
                    except Exception as exc:
                        last_error = exc
                        if chain_choice is None or chain_choice.entry_id is None:
                            raise
                        await record_chain_failure(db, chain_choice.entry_id, exc)
                        # Persist health even when the outer message flow ultimately fails.
                        await db.commit()
                        logger.warning(
                            f"⚠️ Chain provider failed: {chain_choice.reason}: {exc}"
                        )
                else:
                    if last_error is not None:
                        raise last_error
                    raise RuntimeError("Managed AI chain has no eligible provider")

                response = {
                    "content": response_content,
                    "provider": usage_provider,
                    "model": effective_model,
                    "tokens_used": None,
                }

            else:
                # Usar generación normal sin agente
                logger.info("💬 Using standard generation (no agent)")

                async def _generate(provider: str, model: str):
                    """Inner function para usar con rate limit handler."""
                    _provider_instance = UnifiedAIProvider(
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                    )
                    return await _provider_instance.generate_response(
                        messages=context_messages,
                        system_prompt=system_prompt,
                    )

                # Ejecutar con manejo inteligente de rate limits
                response = await generate_with_rate_limit_handling(
                    generate_func=_generate,
                    provider=effective_provider,
                    model=effective_model,
                    estimated_tokens=config.max_tokens,
                    enable_queue=True,
                    enable_retry=True,
                    enable_fallback=True,
                )

            processing_time = int((time.time() - start_time) * 1000)

            # 8. Guardar respuesta en historial
            await ConversationMemory.save_message(
                db=db,
                conversation_id=conversation.id,
                role="assistant",
                content=response["content"],
                provider=response["provider"],
                model=response["model"],
                tokens_used=response["tokens_used"],
                processing_time_ms=processing_time,
            )

            # 9. Actualizar metadata de conversación
            conversation.message_count += 2  # user + assistant
            await db.commit()

            logger.info(
                f"Generated AI response for {from_phone} in {processing_time}ms "
                f"using {response['provider']}/{response['model']}"
            )

            return response["content"]

        except RateLimitError as e:
            # Rate limit específico - enviar mensaje amigable al usuario
            logger.warning(f"⏳ Rate limit hit for {from_phone}: {e}", exc_info=False)
            user_message = get_user_friendly_error_message(e)
            return user_message

        except Exception as e:
            logger.error(f"Error processing incoming message: {e}", exc_info=True)

            # Intentar enviar mensaje de error amigable al usuario
            try:
                user_message = get_user_friendly_error_message(e)
                return user_message
            except Exception:
                # Si falla el mensaje amigable, retornar None para no responder
                return None

    @staticmethod
    async def test_configuration(
        db: AsyncSession,
        config_id: UUID,
        test_message: str = "Hola, ¿cómo estás?",
    ) -> dict:
        """
        Prueba una configuración de IA sin guardar en el historial.

        Args:
            db: Sesión de base de datos
            config_id: ID de la configuración a probar
            test_message: Mensaje de prueba

        Returns:
            Diccionario con resultado de la prueba
        """
        start_time = time.time()

        try:
            config = await AIAssistantService.get_config(db, config_id)

            if not config:
                return {
                    "success": False,
                    "error": "Configuration not found",
                }

            # Preparar system prompt
            system_prompt = config.system_prompt or ""
            if config.auto_enhance_prompt:
                system_prompt = PromptEnhancer.enhance_prompt(system_prompt)

            # Crear proveedor
            # Generar respuesta de prueba con rate limit handling
            api_key = decrypt_api_key(config.api_key_encrypted)

            async def _generate_test(provider: str, model: str):
                """Inner function para usar con rate limit handler."""
                provider_instance = UnifiedAIProvider(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
                return await provider_instance.generate_response(
                    messages=[{"role": "user", "content": test_message}],
                    system_prompt=system_prompt,
                )

            # Ejecutar con rate limit handling
            response = await generate_with_rate_limit_handling(
                generate_func=_generate_test,
                provider=config.provider,
                model=config.model,
                estimated_tokens=config.max_tokens,
                enable_queue=True,
                enable_retry=True,
                enable_fallback=False,  # En test no hacer fallback
            )

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "response": response["content"],
                "tokens_used": response["tokens_used"],
                "processing_time_ms": processing_time,
                "provider": response["provider"],
                "model": response["model"],
            }

        except Exception as e:
            logger.error(f"Error testing configuration: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    async def _get_or_create_conversation(
        db: AsyncSession,
        config_id: UUID,
        from_phone: str,
    ) -> WhatsAppAIConversationDB:
        """Obtiene o crea una conversación."""
        result = await db.execute(
            select(WhatsAppAIConversationDB).where(
                WhatsAppAIConversationDB.config_id == config_id,
                WhatsAppAIConversationDB.from_phone == from_phone,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = WhatsAppAIConversationDB(
                config_id=config_id,
                from_phone=from_phone,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        return conversation

    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        config_id: UUID,
        from_phone: str,
    ) -> Optional[WhatsAppAIConversationDB]:
        """Obtiene el historial de conversación con un número."""
        result = await db.execute(
            select(WhatsAppAIConversationDB).where(
                WhatsAppAIConversationDB.config_id == config_id,
                WhatsAppAIConversationDB.from_phone == from_phone,
            )
        )
        return result.scalar_one_or_none()
