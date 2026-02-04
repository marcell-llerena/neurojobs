from pathlib import Path


def find_project_root(start_path: Path | None = None) -> Path:
    """Locate the project root directory by searching for pyproject.toml.

    Traverses upward from the given path (or current file location) until
    finding a directory containing pyproject.toml. Used to establish
    absolute paths for data directories and configuration files.

    Args:
        start_path: Optional starting path for search. Defaults to the
            directory containing this file.

    Returns:
        Path object pointing to the project root directory.

    Raises:
        RuntimeError: If pyproject.toml is not found in any parent
            directory.
    """
    current = (start_path or Path(__file__)).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("Could not find project root")


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CV_DIR = DATA_DIR / "resumes"
DEFAULT_DB_PATH = DATA_DIR / "sqlite" / "neurojobs.db"
DEFAULT_CHROMA_DIR = DATA_DIR / "chroma"
DEFAULT_CHECKPOINTER_PATH = DATA_DIR / "sqlite" / "checkpoints.db"
