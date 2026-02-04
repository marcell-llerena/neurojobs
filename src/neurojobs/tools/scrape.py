from typing import Any

from langchain.tools import tool
from langchain_core.tools import BaseTool

from neurojobs.ingestion.scraper_pipeline import ScraperPipeline
from neurojobs.scrapers.schemas import JobSearchParams


def make_scrape_tools(scrape_pipeline: ScraperPipeline) -> list[BaseTool]:
    """Create LangChain tools for job scraping operations.

    Args:
        scrape_pipeline: ScraperPipeline instance for executing scraping
            workflows.

    Returns:
        List containing the scrape_jobs tool ready for agent use.
    """

    @tool("scrape_jobs")
    async def scrape_jobs(
        job_title: str, job_location: str, job_limit: int = 10
    ) -> dict[str, Any]:
        """Fetch and process job postings from external sources.

        Use this tool when the user wants to search for jobs or refresh
        the job catalog for a specific job title and geographic location.
        Runs the full scrape pipeline and persists results for later
        matching.

        Args:
            job_title: The job title or role to search for (e.g., "Data
                Scientist", "ML Engineer"). Must be non-empty.
            job_location: The geographic location for the job search
                (e.g., "Remote", "New York, NY"). Must be non-empty.
            job_limit: Maximum number of job postings to scrape. Must be
                between 1 and 60. Defaults to 10.
        Returns:
            On success: {"status": "success", "num_job_postings": int}.
            On failure: {"status": "error", "next_step": "scrape_jobs",
            "instruction": str}. The instruction suggests retrying or
            contacting support.
        """
        processed_job_postings = await scrape_pipeline.run(
            JobSearchParams(
                job_title=job_title, job_location=job_location, job_limit=job_limit
            )
        )

        if processed_job_postings is None:
            return {
                "status": "error",
                "next_step": "scrape_jobs",
                "instruction": "Please try again later or contact support.",
            }

        return {
            "status": "success",
            "num_job_postings": len(processed_job_postings.items),
        }

    return [scrape_jobs]
