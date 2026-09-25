"""
State definitions for LangGraph RAG Agent.

This agent works with a SINGLE knowledge base but can make MULTIPLE
strategic queries to gather and compare information.
"""

import operator
from typing import Annotated, List, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """Result from a single RAG query."""

    content: str
    score: float
    document_name: str
    chunk_index: int
    metadata: dict = Field(default_factory=dict)
    query_used: str = ""  # Track which query generated this result


class QueryPlan(BaseModel):
    """Plan for multiple queries to the same knowledge base."""

    queries: List[str] = Field(
        description="List of specific queries to make to the knowledge base to gather all needed information"
    )
    reasoning: str = Field(description="Explanation of why these queries are needed")


class AgentState(TypedDict):
    """
    State for the RAG Agent.

    This state is passed between nodes in the LangGraph workflow.
    The agent works with ONE knowledge base but can make MULTIPLE queries.
    """

    # User input
    messages: Annotated[List[dict], operator.add]

    # Original query from user
    original_query: str

    # System prompt to follow
    system_prompt: str

    # Single knowledge base to search
    knowledge_base_id: UUID
    knowledge_base_name: str

    # Search parameters
    top_k: int
    min_score: float

    # Queries executed so far
    queries_executed: Annotated[List[str], operator.add]

    # Results from all searches
    search_results: Annotated[List[RAGResult], operator.add]

    # Combined context for synthesis
    combined_context: str

    # Final response
    response: Optional[str]

    # Iteration counter
    iteration: int

    # Max iterations allowed
    max_iterations: int

    # Error tracking
    errors: Annotated[List[str], operator.add]

    # Metadata
    metadata: dict


class SearchDecision(BaseModel):
    """Decision on whether to search more or synthesize."""

    should_search_more: bool = Field(
        description="Whether to perform another search in the knowledge base"
    )
    next_query: Optional[str] = Field(
        default=None,
        description="The next query to execute if should_search_more is True",
    )
    reason: str = Field(description="Reason for the decision")
