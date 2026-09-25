"""
Text chunking strategies for different document types.
"""

import logging
from typing import Any, Dict, List, Optional

import tiktoken
from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Text chunking with different strategies for different content types.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base",
    ):
        """
        Initialize text chunker.

        Args:
            chunk_size: Maximum chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            encoding_name: Tiktoken encoding name
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name

        # Initialize tokenizer for counting
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            logger.warning(
                f"Failed to load {encoding_name}, using cl100k_base"
            )
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk plain text.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dicts with 'content', 'token_count', and 'metadata'
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size * 4,  # Approximate chars per token
            chunk_overlap=self.chunk_overlap * 4,
            length_function=self.count_tokens,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = splitter.split_text(text)

        return [
            {
                "content": chunk,
                "token_count": self.count_tokens(chunk),
                "metadata": {**(metadata or {}), "chunk_type": "text"},
            }
            for chunk in chunks
        ]

    def chunk_markdown(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk markdown text preserving structure.

        Args:
            text: Markdown text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunk dicts
        """
        splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size * 4,
            chunk_overlap=self.chunk_overlap * 4,
        )

        chunks = splitter.split_text(text)

        return [
            {
                "content": chunk,
                "token_count": self.count_tokens(chunk),
                "metadata": {**(metadata or {}), "chunk_type": "markdown"},
            }
            for chunk in chunks
        ]

    def chunk_excel_rows(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk Excel/CSV data by rows.

        Each row becomes a chunk formatted as natural language.

        Args:
            rows: List of row dictionaries
            columns: Column names
            metadata: Optional metadata

        Returns:
            List of chunk dicts
        """
        chunks = []

        for i, row in enumerate(rows):
            # Convert row to natural language
            parts = []
            for col in columns:
                value = row.get(col)
                if value is not None and str(value).strip():
                    parts.append(f"{col}: {value}")

            if parts:
                content = ". ".join(parts)
                chunks.append({
                    "content": content,
                    "token_count": self.count_tokens(content),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_type": "table_row",
                        "row_index": i,
                    },
                })

        return chunks

    def chunk_excel_grouped(
        self,
        rows: List[Dict[str, Any]],
        columns: List[str],
        group_size: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk Excel/CSV data by grouping multiple rows.

        Args:
            rows: List of row dictionaries
            columns: Column names
            group_size: Number of rows per chunk
            metadata: Optional metadata

        Returns:
            List of chunk dicts
        """
        chunks = []

        for i in range(0, len(rows), group_size):
            group = rows[i : i + group_size]
            parts = []

            for j, row in enumerate(group):
                row_parts = []
                for col in columns:
                    value = row.get(col)
                    if value is not None and str(value).strip():
                        row_parts.append(f"{col}: {value}")

                if row_parts:
                    parts.append(f"[Row {i + j + 1}] " + ". ".join(row_parts))

            if parts:
                content = "\n".join(parts)
                token_count = self.count_tokens(content)

                # If chunk is too large, split it
                if token_count > self.chunk_size:
                    # Fall back to individual rows
                    for j, row in enumerate(group):
                        row_parts = []
                        for col in columns:
                            value = row.get(col)
                            if value is not None and str(value).strip():
                                row_parts.append(f"{col}: {value}")

                        if row_parts:
                            row_content = ". ".join(row_parts)
                            chunks.append({
                                "content": row_content,
                                "token_count": self.count_tokens(row_content),
                                "metadata": {
                                    **(metadata or {}),
                                    "chunk_type": "table_row",
                                    "row_index": i + j,
                                },
                            })
                else:
                    chunks.append({
                        "content": content,
                        "token_count": token_count,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_type": "table_group",
                            "start_row": i,
                            "end_row": i + len(group) - 1,
                        },
                    })

        return chunks

    def chunk_pdf_pages(
        self,
        pages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk PDF content by pages with text splitting.

        Args:
            pages: List of page dicts with 'page_num' and 'text'
            metadata: Optional metadata

        Returns:
            List of chunk dicts
        """
        chunks = []

        for page in pages:
            page_text = page.get("text", "").strip()
            if not page_text:
                continue

            page_num = page.get("page_num", 0)
            page_metadata = {
                **(metadata or {}),
                "page_number": page_num,
                "chunk_type": "pdf_page",
            }

            # Check if page fits in one chunk
            token_count = self.count_tokens(page_text)

            if token_count <= self.chunk_size:
                chunks.append({
                    "content": page_text,
                    "token_count": token_count,
                    "metadata": page_metadata,
                })
            else:
                # Split large pages
                page_chunks = self.chunk_text(page_text, page_metadata)
                chunks.extend(page_chunks)

        return chunks

    def chunk_json_objects(
        self,
        objects: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk JSON array by objects.

        Args:
            objects: List of JSON objects
            metadata: Optional metadata

        Returns:
            List of chunk dicts
        """
        import json

        chunks = []

        for i, obj in enumerate(objects):
            # Serialize object to readable string
            content = json.dumps(obj, ensure_ascii=False, indent=2)
            token_count = self.count_tokens(content)

            if token_count <= self.chunk_size:
                chunks.append({
                    "content": content,
                    "token_count": token_count,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_type": "json_object",
                        "object_index": i,
                    },
                })
            else:
                # For large objects, flatten and chunk
                flat_content = self._flatten_json(obj)
                obj_chunks = self.chunk_text(
                    flat_content,
                    {**(metadata or {}), "chunk_type": "json_object", "object_index": i},
                )
                chunks.extend(obj_chunks)

        return chunks

    def _flatten_json(
        self,
        obj: Any,
        prefix: str = "",
    ) -> str:
        """Flatten nested JSON to readable string."""
        lines = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    lines.append(self._flatten_json(value, new_prefix))
                else:
                    lines.append(f"{new_prefix}: {value}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_prefix = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.append(self._flatten_json(item, new_prefix))
                else:
                    lines.append(f"{new_prefix}: {item}")
        else:
            lines.append(f"{prefix}: {obj}")

        return "\n".join(lines)


# Factory function
def get_chunker(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> TextChunker:
    """Get a text chunker instance."""
    return TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
