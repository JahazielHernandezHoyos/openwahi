"""
Tools for RAG Agent to make multiple strategic queries to a single Qdrant collection.

These tools allow the agent to:
- Search with different queries in the same KB
- Refine searches based on previous results
- Compare information across different chunks
- Gather related information piece by piece
"""

import logging
import uuid
from typing import Any, Dict, List

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_base.service import KnowledgeBaseService

logger = logging.getLogger(__name__)


def create_rag_tools(db: AsyncSession, api_key: str) -> List:
    """
    Factory function to create RAG tools with closure over db and api_key.

    Args:
        db: Database session
        api_key: API key for embeddings

    Returns:
        List of tool functions
    """

    @tool
    async def search_knowledge_base(
        query: str,
        knowledge_base_id: str,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base with a specific query.

        Use this tool to search for information in the knowledge base.
        You can call this tool multiple times with different queries to:
        - Compare information (e.g., search for "price of product A" then "price of product B")
        - Gather related information (e.g., search for "features" then search for "specifications")
        - Find more context (e.g., search broadly first, then search specifically)

        Args:
            query: The specific search query (be precise and focused)
            knowledge_base_id: UUID of the knowledge base
            top_k: Number of results to return (default: 5)
            min_score: Minimum similarity score (default: 0.5)

        Returns:
            List of search results with content, score, and metadata
        """
        try:
            kb_uuid = uuid.UUID(knowledge_base_id)

            results = await KnowledgeBaseService.search(
                db=db,
                knowledge_base_ids=[kb_uuid],
                query=query,
                top_k=top_k,
                min_score=min_score,
                api_key=api_key,
            )

            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "content": result.content,
                        "score": result.score,
                        "document_name": result.document_name,
                        "chunk_index": result.chunk_index,
                        "metadata": result.metadata,
                        "query_used": query,  # Track which query found this
                    }
                )

            logger.info(
                f"Search '{query[:50]}...' found {len(formatted_results)} results"
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}", exc_info=True)
            return [{"error": str(e), "query": query}]

    @tool
    async def search_with_different_terms(
        terms: List[str],
        knowledge_base_id: str,
        top_k: int = 3,
        min_score: float = 0.5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for multiple terms and get results for each.

        Use this when you need to compare or gather information about different things.
        For example:
        - Compare prices: terms=["precio producto A", "precio producto B"]
        - Compare features: terms=["características X", "características Y"]
        - Gather related info: terms=["especificaciones", "garantía", "envío"]

        Args:
            terms: List of search terms to look up
            knowledge_base_id: UUID of the knowledge base
            top_k: Number of results per term (default: 3)
            min_score: Minimum similarity score (default: 0.5)

        Returns:
            Dictionary mapping each term to its results
        """
        try:
            kb_uuid = uuid.UUID(knowledge_base_id)
            results_by_term = {}

            for term in terms:
                results = await KnowledgeBaseService.search(
                    db=db,
                    knowledge_base_ids=[kb_uuid],
                    query=term,
                    top_k=top_k,
                    min_score=min_score,
                    api_key=api_key,
                )

                formatted_results = []
                for result in results:
                    formatted_results.append(
                        {
                            "content": result.content,
                            "score": result.score,
                            "document_name": result.document_name,
                            "chunk_index": result.chunk_index,
                            "metadata": result.metadata,
                            "query_used": term,
                        }
                    )

                results_by_term[term] = formatted_results

            total_results = sum(len(r) for r in results_by_term.values())
            logger.info(
                f"Multi-term search found {total_results} total results across {len(terms)} terms"
            )

            return results_by_term

        except Exception as e:
            logger.error(f"Error in multi-term search: {e}", exc_info=True)
            return {"error": str(e)}

    @tool
    async def search_and_expand(
        initial_query: str,
        knowledge_base_id: str,
        expansion_queries: List[str],
        top_k: int = 3,
        min_score: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Search with an initial query, then expand with related queries.

        Use this for a two-phase search:
        1. Initial broad search to find relevant area
        2. Expansion queries to get specific details

        For example:
        - initial_query: "productos disponibles"
        - expansion_queries: ["precios de productos", "características de productos"]

        Args:
            initial_query: The first broad query
            knowledge_base_id: UUID of the knowledge base
            expansion_queries: List of follow-up queries for details
            top_k: Number of results per query (default: 3)
            min_score: Minimum similarity score (default: 0.5)

        Returns:
            Dictionary with 'initial' results and 'expansions' results
        """
        try:
            kb_uuid = uuid.UUID(knowledge_base_id)

            # Initial search
            initial_results = await KnowledgeBaseService.search(
                db=db,
                knowledge_base_ids=[kb_uuid],
                query=initial_query,
                top_k=top_k,
                min_score=min_score,
                api_key=api_key,
            )

            formatted_initial = []
            for result in initial_results:
                formatted_initial.append(
                    {
                        "content": result.content,
                        "score": result.score,
                        "document_name": result.document_name,
                        "chunk_index": result.chunk_index,
                        "metadata": result.metadata,
                        "query_used": initial_query,
                    }
                )

            # Expansion searches
            expansion_results = {}
            for exp_query in expansion_queries:
                exp_results = await KnowledgeBaseService.search(
                    db=db,
                    knowledge_base_ids=[kb_uuid],
                    query=exp_query,
                    top_k=top_k,
                    min_score=min_score,
                    api_key=api_key,
                )

                formatted_exp = []
                for result in exp_results:
                    formatted_exp.append(
                        {
                            "content": result.content,
                            "score": result.score,
                            "document_name": result.document_name,
                            "chunk_index": result.chunk_index,
                            "metadata": result.metadata,
                            "query_used": exp_query,
                        }
                    )

                expansion_results[exp_query] = formatted_exp

            logger.info(
                f"Search and expand: {len(formatted_initial)} initial + "
                f"{sum(len(r) for r in expansion_results.values())} expansion results"
            )

            return {
                "initial": formatted_initial,
                "expansions": expansion_results,
            }

        except Exception as e:
            logger.error(f"Error in search and expand: {e}", exc_info=True)
            return {"error": str(e)}

    return [
        search_knowledge_base,
        search_with_different_terms,
        search_and_expand,
    ]
