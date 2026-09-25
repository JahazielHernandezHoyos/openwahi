"""
Agente LangGraph con herramientas dinámicas.
"""

import logging
import operator
from typing import Annotated, List, TypedDict
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from .response_naturalizer import naturalize
from .tool_loader import DynamicToolLoader

logger = logging.getLogger(__name__)

# Instrucción que se inyecta siempre al final del system prompt para evitar
# que el agente afirme haber ejecutado acciones que no ejecutó (issue #16 Bug 2)
_HONESTY_GUARD = """
REGLA CRÍTICA — acciones y herramientas:
- NUNCA afirmes haber realizado una acción que no ejecutaste (ej: "ya te registré", "ya te agregué").
- Solo confirma una acción DESPUÉS de que la herramienta la ejecute exitosamente.
- Si no tienes el dato requerido (ej: email), pídelo primero. No inventes ni asumas.
"""


class AgentState(TypedDict):
    """Estado del agente."""

    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str


async def create_agent_with_dynamic_tools(
    db: AsyncSession,
    user_id: str,
    llm,
    system_prompt: str,
):
    """
    Crea un agente LangGraph con herramientas dinámicas.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        llm: Modelo de lenguaje
        system_prompt: Prompt del sistema

    Returns:
        Agente compilado listo para usar
    """

    # 1. Cargar herramientas dinámicamente
    tools = await DynamicToolLoader.load_tools_for_user(db, user_id)

    if tools:
        logger.info(f"🛠️ Loaded {len(tools)} tools: {[t.name for t in tools]}")
    else:
        logger.info("ℹ️ No tools loaded, agent will work without tools")

    # 2. Bind tools al LLM (solo si hay herramientas)
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    # 3. Definir nodos del grafo
    async def agent_node(state: AgentState):
        """Nodo del agente - decide qué hacer."""
        messages = state["messages"]

        # Agregar system prompt + honesty guard al inicio
        full_messages = [SystemMessage(content=system_prompt + _HONESTY_GUARD)] + messages

        # LLM decide si llamar herramientas
        response = await llm_with_tools.ainvoke(full_messages)

        return {"messages": [response]}

    # 4. Función de ruteo
    def should_continue(state: AgentState):
        """Decide si continuar llamando herramientas o terminar."""
        last_message = state["messages"][-1]

        # Si el LLM decidió llamar herramientas
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Si no, terminar
        return END

    # 5. Construir el grafo
    workflow = StateGraph(AgentState)

    # Agregar nodo del agente
    workflow.add_node("agent", agent_node)

    # Agregar nodo de herramientas solo si hay herramientas
    if tools:
        tool_node = ToolNode(tools)
        workflow.add_node("tools", tool_node)

    # Entry point
    workflow.set_entry_point("agent")

    # Ruteo condicional
    if tools:
        workflow.add_conditional_edges(
            "agent", should_continue, {"tools": "tools", END: END}
        )

        # Después de ejecutar herramientas, volver al agente
        workflow.add_edge("tools", "agent")
    else:
        # Sin herramientas, siempre terminar
        workflow.add_edge("agent", END)

    # 6. Compilar
    agent = workflow.compile()

    return agent


async def process_message_with_agent(
    db: AsyncSession,
    user_id: str,
    llm,
    system_prompt: str,
    message_text: str,
    # Nuevos parámetros para tracking de uso
    provider: str = "groq",
    model: str = "",
    is_managed: bool = False,
    config_id=None,
    conversation_id=None,
) -> str:
    """
    Procesa un mensaje usando el agente LangGraph.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        llm: Modelo de lenguaje
        system_prompt: Prompt del sistema
        message_text: Mensaje del usuario
        provider: Proveedor del LLM (para tracking de uso)
        model: Nombre del modelo (para tracking de uso)
        is_managed: Si usa clave gestionada por la plataforma
        config_id: ID de configuración del asistente
        conversation_id: ID de la conversación

    Returns:
        Respuesta del agente
    """
    try:
        # Crear agente
        agent = await create_agent_with_dynamic_tools(
            db=db, user_id=user_id, llm=llm, system_prompt=system_prompt
        )

        # Estado inicial
        initial_state = {
            "messages": [HumanMessage(content=message_text)],
            "user_id": str(user_id),
        }

        # Ejecutar agente
        logger.info(f"🤖 Running LangGraph agent for message: {message_text[:50]}...")
        result = await agent.ainvoke(initial_state)

        # Extraer respuesta final
        final_message = result["messages"][-1]

        # Capturar tokens de uso si están disponibles
        tokens_input = 0
        tokens_output = 0
        if hasattr(final_message, "usage_metadata") and final_message.usage_metadata:
            meta = final_message.usage_metadata
            tokens_input = meta.get("input_tokens", 0)
            tokens_output = meta.get("output_tokens", 0)

        # Registrar uso (no bloquea si falla)
        from .usage_tracker import record_usage
        await record_usage(
            db=db,
            user_id=str(user_id),
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            is_managed=is_managed,
            config_id=config_id,
            conversation_id=conversation_id,
        )

        if isinstance(final_message, AIMessage):
            return naturalize(final_message.content)
        else:
            return naturalize(str(final_message.content))

    except Exception as e:
        # Groq ocasionalmente falla con tool_use_failed cuando el modelo genera
        # sintaxis malformada en el tool call. Reintentamos sin tools como fallback.
        error_str = str(e)
        if "tool_use_failed" in error_str or "Failed to call a function" in error_str:
            logger.warning(
                f"⚠️ Groq tool_use_failed detected, retrying without tools: {error_str[:200]}"
            )
            try:
                fallback_messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=message_text),
                ]
                fallback_response = await llm.ainvoke(fallback_messages)
                logger.info("✅ Fallback (no tools) succeeded")

                # Capturar tokens del fallback también
                fb_tokens_in = 0
                fb_tokens_out = 0
                if hasattr(fallback_response, "usage_metadata") and fallback_response.usage_metadata:
                    meta = fallback_response.usage_metadata
                    fb_tokens_in = meta.get("input_tokens", 0)
                    fb_tokens_out = meta.get("output_tokens", 0)
                from .usage_tracker import record_usage
                await record_usage(
                    db=db, user_id=str(user_id), provider=provider, model=model,
                    tokens_input=fb_tokens_in, tokens_output=fb_tokens_out,
                    is_managed=is_managed, config_id=config_id, conversation_id=conversation_id,
                )
                return naturalize(fallback_response.content)
            except Exception as fallback_e:
                logger.error(f"Fallback also failed: {fallback_e}", exc_info=True)
                raise fallback_e

        logger.error(f"Error in LangGraph agent: {e}", exc_info=True)
        raise
