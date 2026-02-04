import emoji
from loguru import logger

from neurojobs.processors.schemas import ProcessedJobPosting
from neurojobs.processors.schemas import ProcessedJobPostings
from neurojobs.scrapers.schemas import RawJobPosting
from neurojobs.scrapers.schemas import RawJobPostings


class PostingProcessor:
    """Processes and normalizes raw job postings into structured format.

    Handles validation, text cleaning (emoji removal, whitespace
    normalization), and filtering of invalid postings. Converts raw scraper
    output into ProcessedJobPosting objects ready for storage.
    """

    @classmethod
    def process(cls, postings: RawJobPostings) -> ProcessedJobPostings:
        """Process a batch of raw job postings into normalized format.

        Validates required fields, cleans text content, and filters out
        invalid entries. Returns only successfully processed postings.

        Args:
            postings: RawJobPostings object from scraper output.

        Returns:
            ProcessedJobPostings object containing validated and cleaned
            job postings. May be empty if all postings are invalid.
        """
        if not postings.items:
            logger.info("No postings to process")
            return ProcessedJobPostings()

        logger.info("Processing {} postings", len(postings.items))
        processed_postings = [
            processed_posting
            for posting in postings.items
            if (processed_posting := cls._process_single_posting(posting))
        ]

        logger.info("Successfully processed {} postings", len(processed_postings))
        return ProcessedJobPostings(items=processed_postings)

    @classmethod
    def _process_single_posting(
        cls, posting: RawJobPosting
    ) -> ProcessedJobPosting | None:
        """Process a single raw job posting into normalized format.

        Validates required fields exist and are non-empty, then applies
        text cleaning and constructs ProcessedJobPosting object.

        Args:
            posting: RawJobPosting object to process.

        Returns:
            ProcessedJobPosting object on success, None if validation
            fails or processing error occurs.
        """
        try:
            if not PostingProcessor._has_required_fields(posting):
                return None

            return ProcessedJobPosting(
                job_id=posting.job_id,
                source=posting.source,
                title=PostingProcessor._clean_text(posting.title),
                company=PostingProcessor._clean_text(posting.company),
                location=PostingProcessor._clean_text(posting.location),
                description=PostingProcessor._clean_text(posting.description),
                url=posting.url,
            )
        except Exception:
            logger.exception("Failed to process posting")
            return None

    @staticmethod
    def _has_required_fields(posting: RawJobPosting) -> bool:
        """Validate that a posting contains all required fields.

        Checks that title, company, location, description, and URL are
        present and non-empty after stripping whitespace.

        Args:
            posting: RawJobPosting object to validate.

        Returns:
            True if all required fields are present and non-empty,
            False otherwise.
        """
        return all(
            (
                posting.title and posting.title.strip(),
                posting.company and posting.company.strip(),
                posting.location and posting.location.strip(),
                posting.description and posting.description.strip(),
                posting.url and posting.url.strip(),
            )
        )

    @staticmethod
    def _clean_text(text: str | None) -> str:
        """Clean and normalize text content.

        Removes emojis, normalizes whitespace (collapses multiple spaces
        to single), and strips leading/trailing whitespace. Returns
        empty string for None or empty input.

        Args:
            text: Raw text string to clean, or None.

        Returns:
            Cleaned text string, or empty string if input is None/empty.
        """
        if not text or not text.strip():
            return ""
        cleaned = emoji.replace_emoji(text.strip(), replace=" ")
        return " ".join(cleaned.split())
