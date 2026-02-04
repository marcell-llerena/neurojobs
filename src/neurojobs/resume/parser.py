from pathlib import Path

import pymupdf


class ResumeParser:
    """Parses PDF resume files to extract raw text content.

    Handles PDF file validation, text extraction using PyMuPDF, and
    basic error handling for malformed or empty documents.
    """

    @staticmethod
    def parse(file_path: str) -> str:
        """Extract text content from a PDF resume file.

        Validates file existence and PDF format, then extracts text from
        all pages using PyMuPDF. Returns concatenated text with minimal
        formatting preservation.

        Args:
            file_path: Path to the PDF file to parse.

        Returns:
            Extracted text content from all pages, joined with newlines.

        Raises:
            FileNotFoundError: If the file does not exist at the
                specified path.
            ValueError: If the file is not a PDF (wrong extension) or
                contains no extractable text.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File {file_path} is not a PDF file")

        text = ResumeParser._extract_text_from_pdf(file_path)
        if not text.strip():
            raise ValueError(f"No text found in {file_path}")

        return text

    @staticmethod
    def _extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text from all pages of a PDF document.

        Opens the PDF, iterates through all pages, extracts text from
        each page, and joins them with newline separators. Empty pages
        are skipped.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Concatenated text from all non-empty pages.
        """
        with pymupdf.open(pdf_path) as pdf:
            text_splits = [
                page.strip()
                for page_num in range(pdf.page_count)
                if (page := str(pdf.load_page(page_num).get_text()))
            ]
        return "\n".join(text_splits)
