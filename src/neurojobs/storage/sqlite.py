import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from neurojobs.processors.schemas import ProcessedJobPostings
from neurojobs.resume.schemas import ExtractedResume


class SQLiteStorage:
    """SQLite-based persistence layer for job postings and resume data.

    Manages relational storage for job posting metadata and candidate
    resume profiles. Handles database initialization, job posting CRUD
    operations, resume storage with embeddings, and time-based queries.
    Uses WAL mode for better concurrency and configures pragmas for
    production use.

    Attributes:
        _db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Create and configure a SQLite database connection.

        Ensures parent directory exists, opens connection, sets row
        factory for dict-like access, and configures pragmas for WAL
        mode, foreign keys, and timeout handling.

        Returns:
            Configured SQLite connection ready for queries.
        """
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")

        return conn

    def _init_db(self) -> None:
        """Initialize database schema if tables do not exist.

        Creates job_postings and resumes tables with appropriate columns
        and constraints. Idempotent operation safe to call multiple
        times.
        """
        with self._connect() as conn:
            # Job postings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_postings (
                    job_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    processed_id TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
            """)

            # CV profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resumes (
                    full_name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    education TEXT,
                    experience TEXT,
                    skills TEXT,
                    projects TEXT,
                    certifications TEXT,
                    embedding_model TEXT,
                    embedding_vector BLOB,
                    embedding_dim INTEGER
                )
            """)

            conn.commit()

    def create_job_postings(self, postings: ProcessedJobPostings) -> None:
        """Insert processed job postings into the database.

        Bulk inserts job posting records with conflict handling (duplicate
        job_ids are ignored). Uses executemany for efficient batch
        insertion.

        Args:
            postings: ProcessedJobPostings object containing items to
                insert. If empty, operation is skipped.
        """
        rows = [
            (
                posting.job_id,
                posting.source,
                posting.url,
                posting.title,
                posting.company,
                posting.location,
                posting.description,
                postings.processed_id,
                postings.processed_at,
            )
            for posting in postings.items
        ]

        if not rows:
            return

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO job_postings (job_id, source, url, title, company, location,
                description, processed_id, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO NOTHING
                """,
                rows,
            )
            conn.commit()

    def get_job_ids_last_days(self, days: int = 7) -> list[str]:
        """Retrieve job IDs ingested within the last N days.

        Queries job_postings table for records where processed_at falls
        within the specified time window. Used for filtering recent jobs
        in matching workflows.

        Args:
            days: Number of days to look back from current time. Must be
                greater than 0.

        Returns:
            List of job_id strings for matching postings.

        Raises:
            ValueError: If days is less than or equal to 0.
        """
        if days <= 0:
            raise ValueError("Days must be greater than 0")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_id
                FROM job_postings
                WHERE datetime(processed_at) >= datetime('now', ?)
                """,
                (f"-{days} days",),
            ).fetchall()

        return [row["job_id"] for row in rows]

    def get_job_by_id(
        self,
        job_id: str | list[str],
        fields: str | list[str] = "*",
    ) -> list[dict[str, Any]]:
        """Retrieve job posting records by job ID(s).

        Supports single or multiple job IDs and flexible field selection.
        Returns results as dictionaries for easy access.

        Args:
            job_id: Single job ID string or list of job IDs to query.
            fields: Field names to retrieve ("*" for all, or list of
                specific column names).

        Returns:
            List of dictionaries, each representing one job posting with
            requested fields. Empty list if no matches found.
        """
        if isinstance(fields, str):
            fields = [fields]

        if isinstance(job_id, str):
            job_id = [job_id]

        fields_str = ",".join(fields)
        placeholders = ",".join(["?"] * len(job_id))

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT {fields_str}
                FROM job_postings
                WHERE job_id IN ({placeholders})""",
                job_id,
            ).fetchall()

        return [dict(row) for row in rows]

    def create_resume(
        self,
        resume: ExtractedResume,
        embedding: np.ndarray | None = None,
        embedding_model: str | None = None,
    ) -> None:
        """Store a resume profile with optional embedding vector.

        Replaces any existing resume (single-resume system). Serializes
        structured fields (education, experience, etc.) as JSON. Stores
        embedding as BLOB with dimension metadata.

        Args:
            resume: ExtractedResume object with structured resume data.
            embedding: Optional numpy array containing embedding vector.
            embedding_model: Optional model identifier for the embedding.
        """
        embedding_blob = None
        embedding_dim = None
        if embedding is not None:
            embedding_dim = len(embedding)
            embedding_blob = np.asarray(embedding, dtype=np.float32).tobytes()

        with self._connect() as conn:
            conn.execute("DELETE FROM resumes")
            conn.commit()

            conn.execute(
                """
                INSERT INTO resumes (full_name, email, phone, education, experience,
                skills, projects, certifications, embedding_model, embedding_vector,
                embedding_dim)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resume.full_name,
                    resume.email,
                    resume.phone,
                    json.dumps(resume.education, ensure_ascii=False),
                    json.dumps(resume.experience, ensure_ascii=False),
                    json.dumps(resume.skills, ensure_ascii=False),
                    json.dumps(resume.projects, ensure_ascii=False),
                    json.dumps(resume.certifications, ensure_ascii=False),
                    embedding_model,
                    embedding_blob,
                    embedding_dim,
                ),
            )
            conn.commit()

    def get_resume(self, fields: str | list[str] = "*") -> dict[str, str] | None:
        """Retrieve the stored resume profile.

        Returns the single resume record (system supports one resume).
        JSON fields are returned as strings and must be parsed by caller.

        Args:
            fields: Field names to retrieve ("*" for all, or list of
                specific column names).

        Returns:
            Dictionary with requested resume fields, or None if no resume
            exists in storage.
        """
        with self._connect() as conn:
            if isinstance(fields, str):
                fields = [fields]
            fields_str = ",".join(fields)
            row = conn.execute(f"SELECT {fields_str} FROM resumes").fetchone()

        if not row:
            return None

        return dict(row)

    def get_resume_embedding(self) -> np.ndarray | None:
        """Retrieve the stored resume embedding vector.

        Deserializes the BLOB embedding data back into a numpy array for use
        in vector similarity operations.

        Returns:
            Numpy array of float32 values representing the embedding,
            or None if no embedding exists.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT embedding_vector FROM resumes").fetchone()

        if not row or row["embedding_vector"] is None:
            return None

        return np.frombuffer(row["embedding_vector"], dtype=np.float32)
