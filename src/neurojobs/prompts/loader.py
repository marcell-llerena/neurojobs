from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=32)
def load_prompt(package: str, filename: str) -> str:
    """Load prompt template text from package resources.

    Caches loaded prompts in memory to avoid repeated filesystem reads.
    Uses importlib.resources for package-relative path resolution.

    Args:
        package: Python package name (e.g., "neurojobs.prompts.agent").
        filename: Name of the prompt file within the package directory.

    Returns:
        Text content of the prompt file, decoded as UTF-8.
    """
    return (resources.files(package) / filename).read_text(encoding="utf-8")
