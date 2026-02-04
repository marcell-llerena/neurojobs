from typing import Any

from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from loguru import logger

from neurojobs.storage.chroma import ChromaStorage
from neurojobs.storage.sqlite import SQLiteStorage


def make_match_jobs_tool(
    storage: SQLiteStorage, vector_store: ChromaStorage
) -> list[BaseTool]:
    """Create LangChain tool for job matching operations.

    Args:
        storage: SQLiteStorage instance for resume and job metadata.
        vector_store: ChromaStorage instance for embedding similarity
            search.

    Returns:
        List containing the match_jobs tool ready for agent use.
    """

    @tool("match_jobs")
    def match_jobs(last_days: int = 7, top_k: int = 10) -> dict[str, Any]:
        """Retrieve job recommendations ranked by similarity to user's resume.

        Use this tool when the user wants to see matched jobs. Requires
        an uploaded resume and its embedding (check with
        get_resume_status first).

        Args:
            last_days: Only consider jobs ingested in the last N days.
                Defaults to 7.
            top_k: Maximum number of job recommendations to return,
                ranked by similarity. Defaults to 10.

        Returns:
            One of:

            - Missing resume: {"status": "missing resume", "error": str,
              "next_step": "upload_resume", "instruction": str}. Direct
              the user to upload a resume.

            - No jobs in window: {"status": "success", "resume": dict,
              "jobs": [], "instruction": str}. No jobs were ingested
              in the last_days window.

            - Success with jobs: {"status": "success", "resume": dict,
              "jobs": list}. Each job has title, description, url, and
              distance (similarity score). Resume contains skills,
              experience, projects, certifications, education.
        """
        resume = storage.get_resume(
            fields=["skills", "experience", "projects", "certifications", "education"]
        )
        embedding = storage.get_resume_embedding()

        if resume is None or embedding is None:
            return {
                "status": "missing resume",
                "error": "Resume not found",
                "next_step": "upload_resume",
                "instruction": "Please upload your resume",
            }

        job_ids = storage.get_job_ids_last_days(days=last_days)
        if not job_ids:
            return {
                "status": "success",
                "resume": resume,
                "jobs": [],
                "instruction": "No jobs found in the last 7 days",
            }

        matched_jobs = vector_store.match_jobs(embedding, top_k=top_k, job_ids=job_ids)
        result_ids = matched_jobs.get("ids")
        result_distances = matched_jobs.get("distances")
        ranked_ids = (result_ids[0]) if result_ids else []
        distances = (result_distances[0]) if result_distances else []

        logger.info(f"Ranked IDs: {ranked_ids}")
        logger.info(f"Length of ranked IDs: {len(ranked_ids)}")

        if not ranked_ids:
            return {
                "status": "success",
                "resume": resume,
                "jobs": [],
            }

        jobs = storage.get_job_by_id(
            ranked_ids, fields=["job_id", "title", "description", "url"]
        )
        distance_by_id = dict(zip(ranked_ids, distances, strict=False))

        for job in jobs:
            dist = distance_by_id.get(job["job_id"])
            job["distance"] = float(dist) if dist is not None else None
            job.pop("job_id")

        return {
            "status": "success",
            "resume": resume,
            "jobs": jobs,
        }

    return [match_jobs]
