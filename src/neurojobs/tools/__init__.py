from langchain_core.tools import BaseTool

from neurojobs.ingestion.scraper_pipeline import ScraperPipeline
from neurojobs.storage.chroma import ChromaStorage
from neurojobs.storage.sqlite import SQLiteStorage
from neurojobs.tools.match_jobs import make_match_jobs_tool
from neurojobs.tools.scrape import make_scrape_tools
from neurojobs.tools.status import make_status_tools


def make_tools(
    storage: SQLiteStorage,
    vector_store: ChromaStorage,
    scraper_pipeline: ScraperPipeline,
) -> list[BaseTool]:
    """Create all LangChain tools for the agent.

    Aggregates tools from scrape, match_jobs, and status modules into
    a single list ready for agent configuration.

    Args:
        storage: SQLiteStorage instance for data access operations.
        vector_store: ChromaStorage instance for embedding operations.
        scraper_pipeline: ScraperPipeline instance for job scraping.

    Returns:
        List of BaseTool instances ready for agent use.
    """
    tools: list[BaseTool] = []
    tools.extend(make_scrape_tools(scraper_pipeline))
    tools.extend(make_match_jobs_tool(storage, vector_store))
    tools.extend(make_status_tools(storage))

    return tools
