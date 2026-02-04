from loguru import logger

from neurojobs.resume.extractor import ResumeConfig
from neurojobs.resume.extractor import ResumeExtractor
from neurojobs.resume.parser import ResumeParser
from neurojobs.storage.chroma import ChromaStorage
from neurojobs.storage.sqlite import SQLiteStorage


class ResumePipeline:
    """Orchestrates end-to-end resume/CV processing workflow.

    Handles parsing, extraction, embedding generation, and persistence of
    candidate resumes. Processes PDF documents into structured data using
    LLM-based extraction, generates embeddings for semantic matching, and
    stores both in SQLite.

    Attributes:
        _storage: SQLite storage for resume data persistence.
        _vector_store: ChromaDB storage for embedding generation.
        _config: Configuration for LLM-based resume extraction.
    """

    def __init__(
        self,
        storage: SQLiteStorage,
        vector_store: ChromaStorage,
        config: ResumeConfig,
    ) -> None:
        self._storage = storage
        self._vector_store = vector_store
        self._config = config

    def run(self, file_path: str) -> None:
        """Process a resume PDF file through the complete pipeline.

        Executes the following steps:
        1. Parses PDF to extract raw text
        2. Extracts structured data using LLM (skills, experience, etc.)
        3. Generates embedding vector for semantic matching
        4. Persists resume and embedding to SQLite storage

        Args:
            file_path: Path to the PDF resume file to process.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
            ValueError: If the file is not a PDF or contains no text.
            Exception: Re-raises any exception during processing. Caller
                should handle appropriately.
        """
        try:
            resume_text = ResumeParser.parse(file_path)
            extracted_resume = ResumeExtractor.extract_structured_data(
                resume_text=resume_text,
                config=self._config,
            )
            embedding = self._vector_store.embed_resume(extracted_resume)
            self._storage.create_resume(
                resume=extracted_resume,
                embedding=embedding,
                embedding_model=self._config.model,
            )

        except Exception:
            logger.exception("Failed to run resume pipeline for file: {}", file_path)
            raise
