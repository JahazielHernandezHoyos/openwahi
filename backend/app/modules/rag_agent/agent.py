"""
RAG Agent implementation using LangGraph.

This agent works with a SINGLE knowledge base but can make MULTIPLE strategic
queries to gather, compare, and synthesize information.

Use cases:
- Compare prices across different products mentioned in different chunks
- Gather related information scattered across multiple chunks
- Find specific details by refining searches
- Synthesize information while strictly following the system prompt
"""

import logging
from typing import Any, Dict, Literal
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from .state import AgentState
from .tools import create_rag_tools

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Agentic RAG system using LangGraph for a single knowledge base.

    This agent can:
    - Make multiple strategic queries to the same Qdrant collection
    - Decide what information is needed based on the user's question
    - Compare information across different chunks
    - Gather related information piece by piece
    - Synthesize results while respecting the system prompt
    """

    def __init__(
        self,
        db: AsyncSession,
        llm: BaseChatModel,
        api_key: str,
        knowledge_base_id: UUID,
        knowledge_base_name: str,
        system_prompt: str,
        max_iterations: int = 3,
        top_k: int = 5,
        min_score: float = 0.5,
    ):
        """
        Initialize the RAG Agent for a single knowledge base.

        Args:
            db: Database session
            llm: Language model for the agent
            api_key: API key for embeddings
            knowledge_base_id: UUID of the single knowledge base to query
            knowledge_base_name: Name of the knowledge base
            system_prompt: System prompt to follow when generating responses
            max_iterations: Maximum number of search iterations (default: 3)
            top_k: Number of results per search (default: 5)
            min_score: Minimum similarity score (default: 0.5)
        """
        self.db = db
        self.llm = llm
        self.api_key = api_key
        self.knowledge_base_id = knowledge_base_id
        self.knowledge_base_name = knowledge_base_name
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.top_k = top_k
        self.min_score = min_score

        # Create tools with the KB ID bound
        self.tools = create_rag_tools(db=db, api_key=api_key)

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Graph structure:
        1. START -> planning: Analyze what information is needed
        2. planning -> searching: Execute searches based on plan
        3. searching -> evaluate: Check if more searches are needed
        4. evaluate -> searching (if more needed) OR synthesize (if done)
        5. synthesize -> END: Generate final response following system prompt

        Returns:
            Compiled graph
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("searching", ToolNode(self.tools))
        workflow.add_node("evaluate", self._evaluate_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Define edges
        workflow.add_edge(START, "planning")
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "search": "searching",
                "synthesize": "synthesize",
            },
        )
        workflow.add_edge("searching", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            self._route_after_evaluate,
            {
                "continue": "planning",
                "synthesize": "synthesize",
                "end": END,
            },
        )
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    def _planning_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Planning node: Decide what searches to perform.

        The agent analyzes the user's question and decides what information
        it needs to gather from the knowledge base.

        Args:
            state: Current agent state

        Returns:
            Updated state with search plan
        """
        original_query = state.get("original_query", "")
        queries_executed = state.get("queries_executed", [])
        search_results = state.get("search_results", [])
        iteration = state.get("iteration", 0)

        # Build planning prompt
        planning_context = f"""🚨 REGLAS ESTRICTAS:
- SOLO puedes buscar información en la base de conocimientos "{self.knowledge_base_name}"
- NO puedes inventar o usar conocimiento general
- Si no encuentras información, debes decirlo claramente

Pregunta del usuario: "{original_query}"

Búsquedas ya realizadas: {len(queries_executed)}
Resultados encontrados hasta ahora: {len(search_results)}

"""

        if queries_executed:
            planning_context += "\nBúsquedas previas:\n"
            for i, q in enumerate(queries_executed, 1):
                planning_context += f"{i}. {q}\n"

        if search_results:
            planning_context += (
                "\nYa tenemos " + str(len(search_results)) + " resultados.\n"
            )

        planning_context += """
Tu tarea es decidir qué herramienta usar para buscar EN LA BASE DE CONOCIMIENTOS.

Herramientas disponibles:
1. search_knowledge_base: Busca con una query específica
2. search_with_different_terms: Busca múltiples términos para comparar
3. search_and_expand: Búsqueda amplia seguida de búsquedas específicas

Estrategia de búsqueda:
- Si necesitas COMPARAR (ej: "precio del Samsung vs iPhone"), usa search_with_different_terms
- Si necesitas DETALLES (ej: "características completas"), usa search_and_expand
- Si necesitas algo ESPECÍFICO (ej: "precio del Samsung S24"), usa search_knowledge_base

🚨 IMPORTANTE:
- Busca términos EXACTOS que puedan estar en los documentos
- Si el usuario pregunta por "productos", busca variaciones como "smartphone", "laptop", "producto"
- Sé específico con las queries
"""

        messages = [
            SystemMessage(content=planning_context),
            HumanMessage(
                content=f"¿Qué debo buscar en la base de conocimientos para responder: '{original_query}'?"
            ),
        ]

        try:
            response = self.llm_with_tools.invoke(messages)

            logger.info(
                f"Planning iteration {iteration + 1}: "
                f"{'Tool call' if hasattr(response, 'tool_calls') and response.tool_calls else 'No tool call'}"
            )

            return {
                "messages": [response],
                "iteration": iteration + 1,
            }

        except Exception as e:
            logger.error(f"Error in planning node: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"Error en planificación: {str(e)}")],
                "errors": [str(e)],
            }

    def _evaluate_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluate node: Decide if more searches are needed.

        Args:
            state: Current agent state

        Returns:
            Updated state with evaluation decision
        """
        original_query = state.get("original_query", "")
        search_results = state.get("search_results", [])
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)

        # Check if we have enough information
        evaluation_prompt = f"""🔍 EVALUACIÓN DE INFORMACIÓN RECOPILADA

Pregunta del usuario: "{original_query}"

Resultados encontrados: {len(search_results)}
Iteraciones realizadas: {iteration} de {max_iterations}

Información recopilada de la base de conocimientos:
"""

        for i, result in enumerate(search_results[:5], 1):  # Show first 5
            if isinstance(result, dict):
                score = result.get("score", 0)
                content = result.get("content", "")
                evaluation_prompt += f"\n{i}. [{score:.2f}] {content[:100]}..."

        evaluation_prompt += """

🚨 EVALUACIÓN CRÍTICA:
¿Los resultados arriba contienen información suficiente para responder la pregunta?

Responde EXACTAMENTE:
- "SUFICIENTE" - Si tienes información clara y relevante para responder
- "MÁS_BÚSQUEDAS: necesito buscar [qué falta]" - Si necesitas más información específica
- "SIN_INFORMACIÓN" - Si después de 2+ búsquedas no encuentras nada relevante

NO digas SUFICIENTE si no tienes información real de los documentos.
"""

        messages = [HumanMessage(content=evaluation_prompt)]

        try:
            response = self.llm.invoke(messages)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            decision = content.strip().upper()

            logger.info(f"Evaluation decision: {decision[:50]}")

            return {
                "messages": [response],
                "metadata": {
                    **state.get("metadata", {}),
                    f"evaluation_{iteration}": decision,
                },
            }

        except Exception as e:
            logger.error(f"Error in evaluation node: {e}", exc_info=True)
            return {
                "errors": [str(e)],
            }

    def _synthesize_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Synthesize results into a final response following the system prompt.

        Args:
            state: Current agent state with search results

        Returns:
            Updated state with final response
        """
        original_query = state.get("original_query", "")
        system_prompt = state.get("system_prompt", "")
        search_results = state.get("search_results", [])
        queries_executed = state.get("queries_executed", [])

        if not search_results:
            return {
                "response": "No encontré información relevante en la base de conocimientos para responder tu pregunta.",
                "combined_context": "",
            }

        try:
            # Build context from all search results
            context_parts = [
                f"### Información de la base de conocimientos '{self.knowledge_base_name}':\n"
            ]

            # Group by query used
            results_by_query = {}
            for result in search_results:
                if isinstance(result, dict):
                    query_used = result.get("query_used", "unknown")
                else:
                    query_used = "unknown"

                if query_used not in results_by_query:
                    results_by_query[query_used] = []
                results_by_query[query_used].append(result)

            # Format grouped results
            for query_used, results in results_by_query.items():
                context_parts.append(f"\n**Búsqueda: '{query_used}'**\n")
                for i, res in enumerate(results[:3], 1):  # Top 3 per query
                    if isinstance(res, dict):
                        content = res.get("content", "")
                        score = res.get("score", 0.0)
                        doc_name = res.get("document_name", "Unknown")
                    else:
                        continue

                    context_parts.append(
                        f"{i}. {content}\n"
                        f"   (Fuente: {doc_name}, Relevancia: {score:.2f})\n"
                    )

            combined_context = "\n".join(context_parts)

            # Create synthesis prompt with STRICT adherence to system prompt
            synthesis_messages = []

            # Add system prompt first with STRICT ANTI-HALLUCINATION rules
            base_system = system_prompt if system_prompt else ""

            strict_system = f"""{base_system}

🚨 REGLAS OBLIGATORIAS ANTI-ALUCINACIÓN:

1. USA SOLAMENTE la información que aparece en los documentos abajo
2. NO inventes precios, productos, o características
3. Si algo no está en los documentos, di "No tengo esa información en mi base de datos"
4. NO uses tu conocimiento general sobre productos
5. Si el usuario pregunta por algo que NO EXISTE en los documentos, dilo claramente
6. SIEMPRE menciona de dónde sacas la información (ej: "Según nuestra base de datos...")

Si no encuentras la información, responde:
"Lo siento, no tengo información sobre [tema] en mi base de datos actual."
"""

            synthesis_messages.append(SystemMessage(content=strict_system))

            # Add context and question
            synthesis_messages.append(
                HumanMessage(
                    content=f"""Pregunta del usuario: {original_query}

{combined_context}

Instrucciones para tu respuesta:
1. Usa SOLAMENTE la información proporcionada arriba
2. Sigue ESTRICTAMENTE el system prompt en tono y formato
3. Si encontraste información de múltiples búsquedas, sintetízala coherentemente
4. Si hay comparaciones (precios, características), preséntalas claramente
5. Menciona las fuentes cuando sea relevante
6. Si la información es insuficiente, indícalo honestamente
7. Responde de manera natural y conversacional

Genera tu respuesta ahora:"""
                )
            )

            # Invoke LLM for synthesis
            response = self.llm.invoke(synthesis_messages)

            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            logger.info(
                f"Synthesized response from {len(search_results)} results "
                f"across {len(queries_executed)} queries"
            )

            return {
                "response": response_text,
                "combined_context": combined_context,
                "messages": [response],
                "metadata": {
                    **state.get("metadata", {}),
                    "total_results": len(search_results),
                    "total_queries": len(queries_executed),
                    "synthesis_complete": True,
                },
            }

        except Exception as e:
            logger.error(f"Error synthesizing results: {e}", exc_info=True)
            return {
                "response": f"Error al generar la respuesta: {str(e)}",
                "combined_context": "",
                "errors": [str(e)],
            }

    def _route_after_planning(
        self, state: AgentState
    ) -> Literal["search", "synthesize"]:
        """Route after planning based on tool calls."""
        messages = state.get("messages", [])
        if not messages:
            return "synthesize"

        last_message = messages[-1]

        # Check if agent wants to make a tool call
        if hasattr(last_message, "tool_calls") and getattr(
            last_message, "tool_calls", None
        ):
            return "search"

        # No tool call = ready to synthesize
        return "synthesize"

    def _route_after_evaluate(
        self, state: AgentState
    ) -> Literal["continue", "synthesize", "end"]:
        """Route after evaluation."""
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", self.max_iterations)
        search_results = state.get("search_results", [])
        messages = state.get("messages", [])

        # Check max iterations
        if iteration >= max_iterations:
            logger.info(f"Max iterations ({max_iterations}) reached")
            return "synthesize"

        # Check if we have no results and hit limit
        if not search_results and iteration >= 2:
            logger.info("No results after 2 iterations, ending")
            return "end"

        # Check evaluation decision
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "content"):
                content = str(last_message.content)
            elif isinstance(last_message, dict):
                content = str(last_message.get("content", ""))
            else:
                content = str(last_message)

            if "SUFICIENTE" in content.upper():
                logger.info("Agent decided it has sufficient information")
                return "synthesize"

            if (
                "SIN_INFORMACIÓN" in content.upper()
                or "SIN_INFORMACION" in content.upper()
            ):
                logger.warning("Agent found NO relevant information after searches")
                return "synthesize"  # Synthesize to give "no info" response

            if "MÁS_BÚSQUEDAS" in content.upper() or "MAS_BUSQUEDAS" in content.upper():
                logger.info("Agent decided to search more")
                return "continue"

        # Default: if we have results, synthesize; otherwise continue
        if search_results:
            return "synthesize"
        else:
            return "continue" if iteration < max_iterations else "end"

    async def query(
        self,
        query: str,
    ) -> Dict[str, Any]:
        """
        Query the RAG agent.

        The agent will make multiple strategic searches to the knowledge base
        and synthesize the information following the system prompt.

        Args:
            query: User's question

        Returns:
            Dict with response, context, results, and metadata
        """
        try:
            # Initial state
            initial_state: AgentState = {
                "messages": [],
                "original_query": query,
                "system_prompt": self.system_prompt,
                "knowledge_base_id": self.knowledge_base_id,
                "knowledge_base_name": self.knowledge_base_name,
                "top_k": self.top_k,
                "min_score": self.min_score,
                "queries_executed": [],
                "search_results": [],
                "combined_context": "",
                "response": None,
                "iteration": 0,
                "max_iterations": self.max_iterations,
                "errors": [],
                "metadata": {
                    "knowledge_base_id": str(self.knowledge_base_id),
                    "knowledge_base_name": self.knowledge_base_name,
                },
            }

            # Run the graph
            logger.info(
                f"Starting RAG agent for KB '{self.knowledge_base_name}' "
                f"with query: {query[:100]}..."
            )

            final_state = await self.graph.ainvoke(initial_state)

            # Extract results
            response = final_state.get("response", "")
            combined_context = final_state.get("combined_context", "")
            search_results = final_state.get("search_results", [])
            queries_executed = final_state.get("queries_executed", [])
            errors = final_state.get("errors", [])

            logger.info(
                f"RAG agent completed. Executed {len(queries_executed)} queries, "
                f"found {len(search_results)} results, errors: {len(errors)}"
            )

            return {
                "response": response,
                "context": combined_context,
                "results": search_results,
                "queries_executed": queries_executed,
                "errors": errors,
                "metadata": {
                    "query": query,
                    "knowledge_base_id": str(self.knowledge_base_id),
                    "knowledge_base_name": self.knowledge_base_name,
                    "num_results": len(search_results),
                    "num_queries": len(queries_executed),
                    "num_errors": len(errors),
                    **final_state.get("metadata", {}),
                },
            }

        except Exception as e:
            logger.error(f"Error in RAG agent query: {e}", exc_info=True)
            return {
                "response": f"Error al procesar la consulta: {str(e)}",
                "context": "",
                "results": [],
                "queries_executed": [],
                "errors": [str(e)],
                "metadata": {
                    "query": query,
                    "error": str(e),
                },
            }


def create_rag_agent(
    db: AsyncSession,
    llm: BaseChatModel,
    api_key: str,
    knowledge_base_id: UUID,
    knowledge_base_name: str,
    system_prompt: str,
    max_iterations: int = 3,
    top_k: int = 5,
    min_score: float = 0.5,
) -> RAGAgent:
    """
    Factory function to create a RAG agent for a single knowledge base.

    Args:
        db: Database session
        llm: Language model
        api_key: API key for embeddings
        knowledge_base_id: UUID of the knowledge base
        knowledge_base_name: Name of the knowledge base
        system_prompt: System prompt to follow
        max_iterations: Maximum search iterations (default: 3)
        top_k: Results per search (default: 5)
        min_score: Minimum similarity score (default: 0.5)

    Returns:
        Configured RAGAgent instance
    """
    return RAGAgent(
        db=db,
        llm=llm,
        api_key=api_key,
        knowledge_base_id=knowledge_base_id,
        knowledge_base_name=knowledge_base_name,
        system_prompt=system_prompt,
        max_iterations=max_iterations,
        top_k=top_k,
        min_score=min_score,
    )
