from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from neurojobs.prompts.loader import load_prompt
from neurojobs.resume.config import ResumeConfig
from neurojobs.resume.schemas import ExtractedResume


class ResumeExtractor:
    """Extracts structured data from resume text using LLM-based parsing.

    Uses LangChain's structured output capabilities to convert raw resume
    text into a normalized ExtractedResume schema. Leverages prompt
    engineering and function calling to extract skills, experience,
    education, and other structured fields.
    """

    @staticmethod
    def _create_llm_extractor(config: ResumeConfig) -> Runnable:
        """Create a LangChain runnable for structured resume extraction.

        Constructs a prompt template with system and human prompts, binds
        it to a ChatOpenAI instance configured for structured output,
        and returns a runnable chain ready for invocation.

        Args:
            config: Resume extraction configuration including model and API
                credentials.

        Returns:
            Runnable chain that accepts resume text and returns
            ExtractedResume object.
        """
        system_prompt = load_prompt("neurojobs.prompts.resume", "system.md")
        human_prompt = load_prompt("neurojobs.prompts.resume", "human.md")

        extraction_prompt = ChatPromptTemplate(
            [("system", system_prompt), ("human", human_prompt)]
        )
        llm = ChatOpenAI(
            model_name=config.model,
            openai_api_key=config.api_key,
            temperature=config.temperature,
            request_timeout=config.request_timeout,
            max_retries=config.max_retries,
        )
        structured_llm = llm.with_structured_output(ExtractedResume)
        return extraction_prompt | structured_llm

    @staticmethod
    def extract_structured_data(
        resume_text: str, config: ResumeConfig
    ) -> ExtractedResume:
        """Extract structured resume data from raw text.

        Processes unstructured resume text through an LLM to produce a
        normalized ExtractedResume object with validated fields for skills,
        experience, education, projects, and certifications.

        Args:
            resume_text: Raw text content extracted from resume PDF.
            config: Configuration for LLM extraction including model and
                API credentials.

        Returns:
            ExtractedResume object with structured resume fields.

        Raises:
            Exception: May raise exceptions from LLM API calls or
                structured output parsing failures.
        """
        llm_extractor = ResumeExtractor._create_llm_extractor(config)
        return llm_extractor.invoke({"resume_text": resume_text})
