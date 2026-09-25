"""
File processing for different document types.
"""

import io
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .chunking import TextChunker, get_chunker
from .models import FileType

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Process different file types and extract text content.
    """

    SUPPORTED_EXTENSIONS = {
        ".xlsx": FileType.XLSX,
        ".xls": FileType.XLS,
        ".csv": FileType.CSV,
        ".pdf": FileType.PDF,
        ".txt": FileType.TXT,
        ".md": FileType.MD,
        ".docx": FileType.DOCX,
        ".json": FileType.JSON,
    }

    MIME_TYPES = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
        "application/vnd.ms-excel": FileType.XLS,
        "text/csv": FileType.CSV,
        "application/pdf": FileType.PDF,
        "text/plain": FileType.TXT,
        "text/markdown": FileType.MD,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
        "application/json": FileType.JSON,
    }

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize file processor.

        Args:
            chunk_size: Chunk size in tokens
            chunk_overlap: Overlap between chunks
        """
        self.chunker = get_chunker(chunk_size, chunk_overlap)

    @classmethod
    def get_file_type(cls, filename: str) -> Optional[FileType]:
        """
        Determine file type from filename extension.

        Args:
            filename: Original filename

        Returns:
            FileType enum or None if unsupported
        """
        import os

        ext = os.path.splitext(filename)[1].lower()
        return cls.SUPPORTED_EXTENSIONS.get(ext)

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        """Check if file type is supported."""
        return cls.get_file_type(filename) is not None

    async def process_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: Optional[FileType] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process a file and return chunks with metadata.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            file_type: Optional explicit file type

        Returns:
            Tuple of (chunks list, document metadata dict)
        """
        if file_type is None:
            file_type = self.get_file_type(filename)

        if file_type is None:
            raise ValueError(f"Unsupported file type: {filename}")

        # Route to appropriate processor
        processors = {
            FileType.XLSX: self._process_excel,
            FileType.XLS: self._process_excel,
            FileType.CSV: self._process_csv,
            FileType.PDF: self._process_pdf,
            FileType.TXT: self._process_text,
            FileType.MD: self._process_markdown,
            FileType.DOCX: self._process_docx,
            FileType.JSON: self._process_json,
        }

        processor = processors.get(file_type)
        if processor is None:
            raise ValueError(f"No processor for file type: {file_type}")

        return await processor(file_content, filename)

    async def _process_excel(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process Excel file (.xlsx, .xls)."""
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(content))

            # Clean data
            df = df.dropna(how="all")  # Remove empty rows
            df = df.fillna("")  # Replace NaN with empty string

            # Convert to records
            columns = df.columns.tolist()
            rows = df.to_dict("records")

            # Chunk by rows
            chunks = self.chunker.chunk_excel_rows(
                rows=rows,
                columns=columns,
                metadata={"source": filename, "file_type": "excel"},
            )

            # Document metadata
            metadata = {
                "total_rows": len(rows),
                "total_columns": len(columns),
                "columns": columns,
                "sheet_count": 1,
            }

            logger.info(
                f"Processed Excel {filename}: {len(rows)} rows, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process Excel file: {e}")
            raise ValueError(f"Failed to process Excel file: {e}")

    async def _process_csv(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process CSV file."""
        try:
            # Try different encodings
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    df = pd.read_csv(
                        io.BytesIO(content),
                        encoding=encoding,
                    )
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV file")

            # Clean data
            df = df.dropna(how="all")
            df = df.fillna("")

            # Convert to records
            columns = df.columns.tolist()
            rows = df.to_dict("records")

            # Chunk by rows
            chunks = self.chunker.chunk_excel_rows(
                rows=rows,
                columns=columns,
                metadata={"source": filename, "file_type": "csv"},
            )

            # Document metadata
            metadata = {
                "total_rows": len(rows),
                "total_columns": len(columns),
                "columns": columns,
            }

            logger.info(
                f"Processed CSV {filename}: {len(rows)} rows, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process CSV file: {e}")
            raise ValueError(f"Failed to process CSV file: {e}")

    async def _process_pdf(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process PDF file."""
        try:
            import fitz  # PyMuPDF

            # Open PDF from bytes
            doc = fitz.open(stream=content, filetype="pdf")

            pages = []
            total_text_length = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                total_text_length += len(text)

                pages.append({
                    "page_num": page_num + 1,
                    "text": text,
                })

            doc.close()

            # Chunk by pages
            chunks = self.chunker.chunk_pdf_pages(
                pages=pages,
                metadata={"source": filename, "file_type": "pdf"},
            )

            # Document metadata
            metadata = {
                "total_pages": len(pages),
                "total_text_length": total_text_length,
            }

            logger.info(
                f"Processed PDF {filename}: {len(pages)} pages, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process PDF file: {e}")
            raise ValueError(f"Failed to process PDF file: {e}")

    async def _process_text(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process plain text file."""
        try:
            # Try different encodings
            text = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("Could not decode text file")

            # Chunk text
            chunks = self.chunker.chunk_text(
                text=text,
                metadata={"source": filename, "file_type": "text"},
            )

            # Document metadata
            metadata = {
                "total_characters": len(text),
                "total_lines": text.count("\n") + 1,
            }

            logger.info(
                f"Processed text {filename}: {len(text)} chars, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process text file: {e}")
            raise ValueError(f"Failed to process text file: {e}")

    async def _process_markdown(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process markdown file."""
        try:
            # Decode
            text = content.decode("utf-8")

            # Chunk markdown
            chunks = self.chunker.chunk_markdown(
                text=text,
                metadata={"source": filename, "file_type": "markdown"},
            )

            # Document metadata
            metadata = {
                "total_characters": len(text),
                "total_lines": text.count("\n") + 1,
            }

            logger.info(
                f"Processed markdown {filename}: {len(text)} chars, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process markdown file: {e}")
            raise ValueError(f"Failed to process markdown file: {e}")

    async def _process_docx(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process Word document (.docx)."""
        try:
            from docx import Document

            # Open document from bytes
            doc = Document(io.BytesIO(content))

            # Extract text from paragraphs
            paragraphs = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)

            # Combine into full text
            full_text = "\n\n".join(paragraphs)

            # Chunk text
            chunks = self.chunker.chunk_text(
                text=full_text,
                metadata={"source": filename, "file_type": "docx"},
            )

            # Document metadata
            metadata = {
                "total_paragraphs": len(paragraphs),
                "total_characters": len(full_text),
            }

            logger.info(
                f"Processed DOCX {filename}: {len(paragraphs)} paragraphs, {len(chunks)} chunks"
            )

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to process DOCX file: {e}")
            raise ValueError(f"Failed to process DOCX file: {e}")

    async def _process_json(
        self,
        content: bytes,
        filename: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process JSON file."""
        try:
            # Parse JSON
            data = json.loads(content.decode("utf-8"))

            # Handle different JSON structures
            if isinstance(data, list):
                # Array of objects
                chunks = self.chunker.chunk_json_objects(
                    objects=data,
                    metadata={"source": filename, "file_type": "json"},
                )
                metadata = {
                    "structure": "array",
                    "total_objects": len(data),
                }
            elif isinstance(data, dict):
                # Single object or nested structure
                # Flatten and chunk
                text = json.dumps(data, ensure_ascii=False, indent=2)
                chunks = self.chunker.chunk_text(
                    text=text,
                    metadata={"source": filename, "file_type": "json"},
                )
                metadata = {
                    "structure": "object",
                    "total_keys": len(data),
                }
            else:
                raise ValueError("JSON must be an object or array")

            logger.info(
                f"Processed JSON {filename}: {len(chunks)} chunks"
            )

            return chunks, metadata

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {e}")
            raise ValueError(f"Invalid JSON file: {e}")
        except Exception as e:
            logger.error(f"Failed to process JSON file: {e}")
            raise ValueError(f"Failed to process JSON file: {e}")


# Factory function
def get_file_processor(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> FileProcessor:
    """Get a file processor instance."""
    return FileProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
