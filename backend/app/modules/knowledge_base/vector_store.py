"""
Vector store interface using Qdrant.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import ResponseHandlingException

from app.config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector store implementation using Qdrant.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            url: Full Qdrant URL, including HTTPS for Qdrant Cloud
            host: Qdrant host
            port: Qdrant port
            api_key: Qdrant API key (for cloud)
        """
        self.url = url or settings.QDRANT_URL
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.dimensions = settings.EMBEDDING_DIMENSIONS

        # Prefer a full URL so Qdrant Cloud always uses HTTPS.
        if self.url:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
            )
        elif self.api_key:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
            )
        else:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
            )

    def _get_collection_name(self, knowledge_base_id: uuid.UUID) -> str:
        """Generate collection name from knowledge base ID."""
        return f"kb_{str(knowledge_base_id).replace('-', '_')}"

    async def create_collection(
        self,
        knowledge_base_id: uuid.UUID,
        dimensions: Optional[int] = None,
    ) -> bool:
        """
        Create a new collection for a knowledge base.

        Args:
            knowledge_base_id: Knowledge base UUID
            dimensions: Vector dimensions (default from settings)

        Returns:
            True if created successfully
        """
        collection_name = self._get_collection_name(knowledge_base_id)
        dims = dimensions or self.dimensions

        try:
            # Check if collection exists
            collections = self.client.get_collections()
            existing_names = [c.name for c in collections.collections]

            if collection_name in existing_names:
                logger.info(f"Collection {collection_name} already exists")
                return True

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=dims,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

            logger.info(f"Created collection: {collection_name}")
            return True

        except ResponseHandlingException as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    async def delete_collection(self, knowledge_base_id: uuid.UUID) -> bool:
        """
        Delete a collection.

        Args:
            knowledge_base_id: Knowledge base UUID

        Returns:
            True if deleted successfully
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True

        except ResponseHandlingException as e:
            logger.error(f"Failed to delete collection: {e}")
            return False

    async def upsert_vectors(
        self,
        knowledge_base_id: uuid.UUID,
        points: List[Dict[str, Any]],
    ) -> bool:
        """
        Upsert vectors into a collection.

        Args:
            knowledge_base_id: Knowledge base UUID
            points: List of dicts with 'id', 'vector', and 'payload'

        Returns:
            True if upserted successfully
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            qdrant_points = [
                qdrant_models.PointStruct(
                    id=str(point["id"]),
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
                for point in points
            ]

            self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )

            logger.info(f"Upserted {len(points)} vectors to {collection_name}")
            return True

        except ResponseHandlingException as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return False

    async def delete_vectors(
        self,
        knowledge_base_id: uuid.UUID,
        point_ids: List[str],
    ) -> bool:
        """
        Delete vectors from a collection.

        Args:
            knowledge_base_id: Knowledge base UUID
            point_ids: List of point IDs to delete

        Returns:
            True if deleted successfully
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.PointIdsList(points=point_ids),
            )

            logger.info(f"Deleted {len(point_ids)} vectors from {collection_name}")
            return True

        except ResponseHandlingException as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def search(
        self,
        knowledge_base_id: uuid.UUID,
        query_vector: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            knowledge_base_id: Knowledge base UUID
            query_vector: Query vector
            top_k: Number of results to return
            min_score: Minimum similarity score
            filter_conditions: Optional filter conditions

        Returns:
            List of search results with 'id', 'score', and 'payload'
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value),
                        )
                        for key, value in filter_conditions.items()
                    ]
                )

            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                score_threshold=min_score,
                query_filter=query_filter,
            ).points

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                }
                for result in results
            ]

        except ResponseHandlingException as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_multiple_collections(
        self,
        knowledge_base_ids: List[uuid.UUID],
        query_vector: List[float],
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search across multiple collections.

        Args:
            knowledge_base_ids: List of knowledge base UUIDs
            query_vector: Query vector
            top_k: Number of results per collection
            min_score: Minimum similarity score

        Returns:
            Combined and sorted search results
        """
        all_results = []

        for kb_id in knowledge_base_ids:
            results = await self.search(
                knowledge_base_id=kb_id,
                query_vector=query_vector,
                top_k=top_k,
                min_score=min_score,
            )
            for result in results:
                result["knowledge_base_id"] = str(kb_id)
            all_results.extend(results)

        # Sort by score and take top_k
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    async def get_collection_info(
        self,
        knowledge_base_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get collection information.

        Args:
            knowledge_base_id: Knowledge base UUID

        Returns:
            Collection info dict or None
        """
        collection_name = self._get_collection_name(knowledge_base_id)

        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }

        except ResponseHandlingException:
            return None


# Factory function
def get_vector_store() -> VectorStore:
    """Get a vector store instance."""
    return VectorStore()
