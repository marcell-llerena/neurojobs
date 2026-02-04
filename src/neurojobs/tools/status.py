from langchain_core.tools import BaseTool
from langchain_core.tools import tool

from neurojobs.storage.sqlite import SQLiteStorage


def make_status_tools(storage: SQLiteStorage) -> list[BaseTool]:
    """Create LangChain tools for resume status checking.

    Args:
        storage: SQLiteStorage instance for resume data access.

    Returns:
        List containing the get_resume_status tool ready for agent use.
    """

    @tool("get_resume_status")
    async def get_resume_status() -> dict[str, bool]:
        """Check whether user has uploaded a resume and embedding exists.

        Use this tool when you need to determine if the user profile is
        ready for job matching, or before suggesting resume upload or
        running match_jobs. Reads from local storage only; no network
        calls.

        Returns:
            Dictionary with two keys:
            - has_profile: True if a resume document exists in storage,
              False otherwise.
            - has_embedding: True if an embedding for the resume
              exists, False otherwise.
        """
        resume = storage.get_resume()
        embedding = storage.get_resume_embedding()
        return {
            "has_profile": resume is not None,
            "has_embedding": embedding is not None,
        }

    return [get_resume_status]
