from loguru import logger

from neurojobs.processors.posting import PostingProcessor
from neurojobs.processors.schemas import ProcessedJobPostings
from neurojobs.scrapers.base import BaseScraper
from neurojobs.scrapers.schemas import JobSearchParams
from neurojobs.storage.chroma import ChromaStorage
from neurojobs.storage.sqlite import SQLiteStorage


class ScraperPipeline:
    """Orchestrates end-to-end job posting ingestion workflow.

    Coordinates scraping, processing, and persistence of job postings
    from external sources. Handles the full pipeline from raw scraping
    to normalized storage in both SQLite (metadata) and ChromaDB
    (embeddings for semantic search).

    Attributes:
        _scraper: Scraper instance for fetching raw job postings.
        _storage: SQLite storage for job posting metadata persistence.
        _vector_store: ChromaDB storage for embedding-based retrieval.
    """

    def __init__(
        self,
        scraper: BaseScraper,
        storage: SQLiteStorage,
        vector_store: ChromaStorage,
    ) -> None:
        self._scraper = scraper
        self._storage = storage
        self._vector_store = vector_store

    async def run(self, search_params: JobSearchParams) -> ProcessedJobPostings | None:
        """Execute the complete job scraping and ingestion pipeline.

        Performs the following steps:
        1. Scrapes raw job postings using the configured scraper
        2. Processes and normalizes job data (cleaning, validation)
        3. Persists processed postings to SQLite storage
        4. Generates embeddings and upserts to vector store

        Args:
            search_params: Search criteria including job title and location.

        Returns:
            ProcessedJobPostings object containing successfully ingested
            postings, or None if no valid postings were found or an
            error occurred during scraping.

        Raises:
            Exception: Re-raises any exception that occurs during
                scraping, processing, or persistence. Caller should
                handle appropriately.
        """
        logger.info(
            "Running LinkedIn scraper pipeline for: job title={} and job location={}",
            search_params.job_title,
            search_params.job_location,
        )

        async with self._scraper as scraper:
            try:
                raw_job_postings = await scraper.scrape(search_params)
                if not raw_job_postings.items:
                    return None

                processed_job_postings = PostingProcessor.process(raw_job_postings)

                if not processed_job_postings.items:
                    return None

                self._storage.create_job_postings(processed_job_postings)
                self._vector_store.upsert_jobs(processed_job_postings)

                return processed_job_postings

            except Exception:
                logger.exception("Unexpected error occurred during scraping")
                raise
