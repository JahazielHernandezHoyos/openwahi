"""
RAG Agent module with LangGraph.

This module provides agentic RAG functionality using LangGraph to:
- Make multiple queries to Qdrant collections
- Combine and synthesize information from different knowledge bases
- Intelligently route queries to the appropriate knowledge bases
"""

from .agent import RAGAgent, create_rag_agent
from .state import AgentState, RAGResult

__all__ = ["RAGAgent", "create_rag_agent", "AgentState", "RAGResult"]
