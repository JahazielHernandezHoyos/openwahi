"""
Herramientas webhook dinámicas para LangGraph.
"""

import logging
from typing import Any, Dict, Optional, Type

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


class WebhookToolConfig(BaseModel):
    """Configuración de una herramienta webhook."""

    name: str
    description: str
    webhook_url: str
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    input_schema: Dict
    auth_type: Optional[str] = None
    auth_value: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    is_enabled: bool = True


class DynamicWebhookTool:
    """Herramienta dinámica que se crea desde configuración."""

    @staticmethod
    def create_pydantic_model(name: str, json_schema: Dict) -> Type[BaseModel]:
        """
        Crea un modelo Pydantic dinámicamente desde JSON Schema.
        """
        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        # Mapeo de tipos JSON Schema a Python
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        # Crear fields del modelo Pydantic
        fields = {}
        for field_name, field_schema in properties.items():
            field_type = field_schema.get("type", "string")
            description = field_schema.get("description", "")
            is_required = field_name in required

            python_type = type_map.get(field_type, str)

            if not is_required:
                python_type = Optional[python_type]
                default = None
            else:
                default = ...

            fields[field_name] = (
                python_type,
                Field(default=default, description=description),
            )

        # Crear modelo dinámicamente
        return create_model(f"{name}Input", **fields)

    @staticmethod
    async def execute_webhook(
        config: WebhookToolConfig, validated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta el webhook con datos validados.
        """
        headers = config.headers.copy()

        # Agregar autenticación
        if config.auth_type == "bearer" and config.auth_value:
            headers["Authorization"] = f"Bearer {config.auth_value}"
        elif config.auth_type == "api_key" and config.auth_value:
            headers["X-API-Key"] = config.auth_value

        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            try:
                logger.info(f"🌐 Calling webhook: {config.webhook_url}")
                logger.info(f"📤 Payload: {validated_data}")

                response = await client.request(
                    method=config.method,
                    url=config.webhook_url,
                    json=validated_data,
                    headers=headers,
                )

                response.raise_for_status()

                result = response.json() if response.text else {"status": "success"}

                logger.info(f"✅ Webhook success: {result}")

                return {
                    "success": True,
                    "data": result,
                    "status_code": response.status_code,
                }

            except httpx.HTTPError as e:
                logger.error(f"❌ Webhook failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "status_code": getattr(e.response, "status_code", None)
                    if hasattr(e, "response")
                    else None,
                }

    @classmethod
    def create_tool(cls, config: WebhookToolConfig):
        """
        Crea una herramienta LangChain desde configuración.
        """
        # Crear modelo Pydantic para validación
        InputModel = cls.create_pydantic_model(config.name, config.input_schema)

        # Crear la función de la herramienta
        async def webhook_function(**kwargs) -> str:
            """
            Función llamada por el agente cuando decide usar la herramienta.
            """
            # Validar con Pydantic
            validated_input = InputModel(**kwargs)

            # Ejecutar webhook
            result = await cls.execute_webhook(
                config=config, validated_data=validated_input.dict()
            )

            if result["success"]:
                response_data = result.get("data", {})

                # Build a clear success message for the agent
                if "message" in response_data:
                    message = response_data["message"]
                else:
                    # Create detailed success message with data
                    message = f"La acción '{config.name}' se completó exitosamente."
                    if response_data:
                        # Include relevant data from response
                        data_str = ", ".join([f"{k}: {v}" for k, v in response_data.items() if k != "message"])
                        if data_str:
                            message += f" Detalles: {data_str}"

                return f"✅ ACCIÓN COMPLETADA: {message}"
            else:
                return f"❌ Error ejecutando {config.name}: {result['error']}"

        # Configurar metadatos
        webhook_function.__name__ = config.name
        webhook_function.__doc__ = config.description

        # Decorar como herramienta LangChain
        return tool(webhook_function, args_schema=InputModel)
