"""
AI Assistant API Router - Endpoints for managing AI configurations.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_user_id

from .models import (
    AIConfigCreate,
    AIConfigResponse,
    AIConfigUpdate,
    AIConversationResponse,
    AIMessageResponse,
    TestMessageRequest,
    TestMessageResponse,
)
from .provider import UnifiedAIProvider
from .service import AIAssistantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


@router.get("/providers", response_model=List[str])
async def get_available_providers():
    """
    Obtiene lista de proveedores de IA disponibles.
    """
    return UnifiedAIProvider.get_available_providers()


@router.get("/providers/{provider}/models", response_model=List[str])
async def get_provider_models(provider: str):
    """
    Obtiene lista de modelos disponibles para un proveedor.
    """
    models = UnifiedAIProvider.get_available_models(provider)
    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' not found",
        )
    return models


@router.post(
    "/devices/{device_id}/configs",
    response_model=AIConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_config(
    device_id: UUID,
    config_data: AIConfigCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Crea una nueva configuración de IA para un dispositivo.

    Solo puede haber UNA configuración por dispositivo.
    El bot responderá a CUALQUIER persona que le escriba.

    El usuario debe proporcionar su propia API key del proveedor de IA.
    """
    # Verificar que el dispositivo pertenece al usuario
    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB

    result = await db.execute(
        select(WhatsAppDeviceDB).where(
            WhatsAppDeviceDB.id == device_id,
            WhatsAppDeviceDB.user_id == user_id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or does not belong to you",
        )

    # Validar proveedor y modelo
    if not UnifiedAIProvider.validate_provider_model(config_data.provider, config_data.model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model '{config_data.model}' for provider '{config_data.provider}'",
        )

    # Verificar si ya existe una configuración para este dispositivo
    existing_configs = await AIAssistantService.list_configs(db, device_id)

    if existing_configs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI configuration already exists for this device. Delete the existing one first or edit it.",
        )

    # Crear configuración
    config = await AIAssistantService.create_config(
        db=db,
        user_id=user_id,
        device_id=device_id,
        phone_number=config_data.phone_number,
        name=config_data.name,
        provider=config_data.provider,
        model=config_data.model,
        api_key=config_data.api_key,
        system_prompt=config_data.system_prompt,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        use_memory=config_data.use_memory,
        memory_window=config_data.memory_window,
        auto_enhance_prompt=config_data.auto_enhance_prompt,
        use_knowledge_base=config_data.use_knowledge_base,
        knowledge_base_ids=config_data.knowledge_base_ids,
        rag_top_k=config_data.rag_top_k,
        rag_min_score=config_data.rag_min_score,
    )

    return config


@router.get("/devices/{device_id}/configs", response_model=List[AIConfigResponse])
async def list_ai_configs(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Lista todas las configuraciones de IA para un dispositivo.
    """
    # Verificar que el dispositivo pertenece al usuario
    from sqlalchemy import select

    from app.modules.whatsapp.models import WhatsAppDeviceDB

    result = await db.execute(
        select(WhatsAppDeviceDB).where(
            WhatsAppDeviceDB.id == device_id,
            WhatsAppDeviceDB.user_id == user_id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or does not belong to you",
        )

    configs = await AIAssistantService.list_configs(db, device_id)
    return configs


@router.get("/configs/{config_id}", response_model=AIConfigResponse)
async def get_ai_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Obtiene una configuración de IA por ID.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    return config


@router.patch("/configs/{config_id}", response_model=AIConfigResponse)
async def update_ai_config(
    config_id: UUID,
    config_data: AIConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Actualiza una configuración de IA.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    # Validar proveedor y modelo si se están actualizando
    if config_data.provider and config_data.model:
        if not UnifiedAIProvider.validate_provider_model(config_data.provider, config_data.model):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model '{config_data.model}' for provider '{config_data.provider}'",
            )

    # Actualizar
    updates = config_data.model_dump(exclude_unset=True)
    updated_config = await AIAssistantService.update_config(db, config_id, **updates)

    return updated_config


@router.post("/configs/{config_id}/toggle")
async def toggle_ai_config(
    config_id: UUID,
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Activa o desactiva una configuración de IA.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    updated_config = await AIAssistantService.toggle_config(db, config_id, enabled)

    return {
        "success": True,
        "message": f"Configuration {'enabled' if enabled else 'disabled'} successfully",
        "config": updated_config,
    }


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Elimina una configuración de IA.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    await AIAssistantService.delete_config(db, config_id)


@router.post("/configs/{config_id}/test", response_model=TestMessageResponse)
async def test_ai_config(
    config_id: UUID,
    test_data: TestMessageRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Prueba una configuración de IA sin guardar en el historial.

    Útil para verificar que la configuración funciona correctamente
    antes de activarla.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    # Ejecutar prueba
    result = await AIAssistantService.test_configuration(db, config_id, test_data.message)

    return result


@router.get(
    "/configs/{config_id}/conversations/{phone}",
    response_model=AIConversationResponse,
)
async def get_conversation_history(
    config_id: UUID,
    phone: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Obtiene el historial de conversación con un número específico.
    """
    config = await AIAssistantService.get_config(db, config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found",
        )

    # Verificar que pertenece al usuario
    if config.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this configuration",
        )

    conversation = await AIAssistantService.get_conversation_history(db, config_id, phone)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


# ==================== Standalone configs (no device required) ====================


@router.post(
    "/configs",
    response_model=AIConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create standalone AI config (no WhatsApp device needed)",
)
async def create_standalone_ai_config(
    config_data: AIConfigCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Crea un AI config standalone — sin dispositivo WhatsApp.

    Útil para widgets embebibles, integraciones vía API, bots de soporte web, etc.
    """
    if not UnifiedAIProvider.validate_provider_model(config_data.provider, config_data.model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model '{config_data.model}' for provider '{config_data.provider}'",
        )

    config = await AIAssistantService.create_config(
        db=db,
        user_id=user_id,
        device_id=None,
        phone_number=config_data.phone_number,
        name=config_data.name,
        provider=config_data.provider,
        model=config_data.model,
        api_key=config_data.api_key,
        system_prompt=config_data.system_prompt,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        use_memory=config_data.use_memory,
        memory_window=config_data.memory_window,
        auto_enhance_prompt=config_data.auto_enhance_prompt,
        use_knowledge_base=config_data.use_knowledge_base,
        knowledge_base_ids=config_data.knowledge_base_ids,
        rag_top_k=config_data.rag_top_k,
        rag_min_score=config_data.rag_min_score,
    )
    return config


@router.get(
    "/configs",
    response_model=List[AIConfigResponse],
    summary="List all AI configs for the current user",
)
async def list_all_ai_configs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Lista todos los AI configs del usuario (con y sin dispositivo WhatsApp).
    """
    configs = await AIAssistantService.list_configs_by_user(db, user_id)
    return configs
