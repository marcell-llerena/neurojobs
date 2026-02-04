from pathlib import Path

import numpy as np
from chromadb import PersistentClient
from chromadb import QueryResult
from chromadb.types import Metadata
from chromadb.types import Where
from chromadb.utils import embedding_functions
from loguru import logger

from neurojobs.processors.schemas import ProcessedJobPosting
from neurojobs.processors.schemas import ProcessedJobPostings
from neurojobs.resume.schemas import ExtractedResume
from neurojobs.storage.config import ChromaConfig


class ChromaStorage:
    """ChromaDB-based vector store for semantic job matching.

    Manages embeddings and similarity search for job postings and resume
    profiles. Uses OpenAI embedding functions for vector generation and
    ChromaDB's persistent client for storage. Supports upsert operations
    with deduplication and query-based matching.

    Attributes:
        _chroma_dir: Directory path for ChromaDB persistence.
        _client: ChromaDB persistent client instance.
        _embedder: OpenAI embedding function for vector generation.
        _job_collection: ChromaDB collection for job posting embeddings.
    """

    def __init__(self, chroma_dir: Path, config: ChromaConfig) -> None:
        self._chroma_dir = chroma_dir
        self._chroma_dir.mkdir(parents=True, exist_ok=True)

        self._client = PersistentClient(path=self._chroma_dir)

        self._embedder = embedding_functions.OpenAIEmbeddingFunction(
            model_name=config.model,
            api_key=config.api_key.get_secret_value(),
        )

        self._job_collection = self._client.get_or_create_collection(
            name="job_postings",
            embedding_function=self._embedder,  # ty:ignore[invalid-argument-type]
        )

    def _build_resume_document(self, resume: ExtractedResume) -> str:
        """Construct a text document from structured resume data.

        Combines resume sections (skills, experience, projects, etc.)
        into a single text document suitable for embedding generation.
        Sections are formatted with labels and newline separators.

        Args:
            resume: ExtractedResume object with structured fields.

        Returns:
            Formatted text document ready for embedding.
        """
        parts: list[str] = []

        if resume.skills:
            parts.append("Skills:\n" + "\n".join(resume.skills))
        if resume.experience:
            parts.append("Experience:\n" + "\n".join(resume.experience))
        if resume.projects:
            parts.append("Projects:\n" + "\n".join(resume.projects))
        if resume.certifications:
            parts.append("Certifications:\n" + "\n".join(resume.certifications))
        if resume.education:
            parts.append("Education:\n" + "\n".join(resume.education))

        return "\n\n".join(parts).strip()

    def _build_job_document(self, job: ProcessedJobPosting) -> str:
        """Construct a text document from job posting data.

        Formats job title and description into a single text document
        suitable for embedding generation.

        Args:
            job: ProcessedJobPosting object with title and description.

        Returns:
            Formatted text document ready for embedding.
        """
        return f"Title: {job.title}\nDescription: {job.description}".strip()

    def embed_resume(self, resume: ExtractedResume) -> np.ndarray:
        """Generate embedding vector for a resume profile.

        Converts structured resume data to text, then generates an
        embedding using the configured OpenAI embedding model.

        Args:
            resume: ExtractedResume object to embed.

        Returns:
            Numpy array containing the embedding vector (float32).
        """
        document = self._build_resume_document(resume)
        vectors = self._embedder.embed_query([document])
        return vectors[0]

    def upsert_jobs(
        self, job_postings: ProcessedJobPostings, only_new: bool = True
    ) -> None:
        """Upsert job posting embeddings into ChromaDB.

        Generates embeddings for job postings and stores them in the
        vector collection. Optionally filters out existing job_ids to
        avoid redundant embedding generation.

        Args:
            job_postings: ProcessedJobPostings object containing jobs to
                upsert.
            only_new: If True, skip jobs that already exist in the
                collection (deduplication). Defaults to True to optimize
                API usage.
        """
        if only_new:
            candidate_ids = [job.job_id for job in job_postings.items]
            existing = self._job_collection.get(ids=candidate_ids, include=[])
            existing_ids = set(existing.get("ids", []))

            job_postings = ProcessedJobPostings(
                items=[
                    job for job in job_postings.items if job.job_id not in existing_ids
                ],
                processed_id=job_postings.processed_id,
                processed_at=job_postings.processed_at,
            )

            if not job_postings.items:
                logger.info("No new job postings to upsert")
                return

        logger.info(f"Upserting {len(job_postings.items)} job postings")

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[Metadata] = []

        for job in job_postings.items:
            url = job.url
            ids.append(job.job_id)
            documents.append(self._build_job_document(job))
            metadatas.append(
                {
                    "job_id": job.job_id,
                    "url": url,
                    "source": job.source,
                    "processed_id": job_postings.processed_id,
                    "processed_at": str(job_postings.processed_at),
                }
            )

        self._job_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def match_jobs(
        self,
        profile_embedding: np.ndarray,
        top_k: int = 10,
        job_ids: list[str] | None = None,
    ) -> QueryResult:
        """Find most similar job postings to a resume embedding.

        Performs vector similarity search using cosine distance. Optionally
        filters to specific job_ids (e.g., recent jobs from last N days).
        Returns ranked results with metadata and distances.

        Args:
            profile_embedding: Numpy array embedding vector for the resume
                profile.
            top_k: Maximum number of results to return, ranked by
                similarity. Defaults to 10.
            job_ids: Optional list of job IDs to restrict search to. If
                None, searches all jobs in collection.

        Returns:
            ChromaDB QueryResult containing ids, documents, metadatas,
            and distances arrays. Results are sorted by similarity
            (lower distance = higher similarity).
        """
        where: Where | None = {"job_id": {"$in": job_ids}} if job_ids else None
        return self._job_collection.query(
            query_embeddings=[profile_embedding],
            n_results=top_k,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
