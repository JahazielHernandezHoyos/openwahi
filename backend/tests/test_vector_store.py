import os
from unittest.mock import patch

os.environ.setdefault("FIREBASE_PROJECT_ID", "test-project")

from app.config.settings import settings
from app.modules.knowledge_base.vector_store import VectorStore


@patch("app.modules.knowledge_base.vector_store.QdrantClient")
def test_vector_store_uses_full_url_for_qdrant_cloud(mock_client):
    with (
        patch.object(settings, "QDRANT_URL", "https://cluster.cloud.qdrant.io"),
        patch.object(settings, "QDRANT_API_KEY", "test-api-key"),
    ):
        VectorStore()

    mock_client.assert_called_once_with(
        url="https://cluster.cloud.qdrant.io",
        api_key="test-api-key",
    )


@patch("app.modules.knowledge_base.vector_store.QdrantClient")
def test_vector_store_keeps_host_and_port_for_local_qdrant(mock_client):
    with (
        patch.object(settings, "QDRANT_URL", None),
        patch.object(settings, "QDRANT_HOST", "qdrant"),
        patch.object(settings, "QDRANT_PORT", 6333),
        patch.object(settings, "QDRANT_API_KEY", None),
    ):
        VectorStore()

    mock_client.assert_called_once_with(host="qdrant", port=6333)
