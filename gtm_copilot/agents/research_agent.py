"""Research Agent for gathering company facts, web intelligence, and internal playbook grounding."""

import html
import logging
import re
from typing import List, Optional, Tuple

import httpx

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.config import (
    MAX_WEB_CONTENT_CHARS,
    WEB_FETCH_TIMEOUT_SECONDS,
)
from gtm_copilot.llm import LLMProvider, extract_json, get_llm_provider
from gtm_copilot.models import ResearchInput, ResearchOutput
from gtm_copilot.retrieval.hybrid_retriever import HybridRetriever
from gtm_copilot.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert B2B Sales & GTM Research Analyst. "
    "Your goal is to extract factual, verified, and structured intelligence "
    "about a target company using the provided website text and internal playbook/account context."
)


def extract_visible_text_from_html(html_content: str, max_chars: int = MAX_WEB_CONTENT_CHARS) -> str:
    """Extract and clean visible text from raw HTML content."""
    if not html_content:
        return ""

    # Remove script and style elements
    cleaned = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)

    # Extract title and meta description if present
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, flags=re.DOTALL | re.IGNORECASE)
    meta_desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html_content, flags=re.IGNORECASE)

    meta_parts = []
    if title_match:
        meta_parts.append(f"Title: {title_match.group(1).strip()}")
    if meta_desc_match:
        meta_parts.append(f"Description: {meta_desc_match.group(1).strip()}")

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", cleaned)
    text = html.unescape(text)

    # Normalize whitespace
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    visible_body = "\n".join([line for line in lines if line])

    combined = "\n".join(meta_parts + [visible_body])
    return combined[:max_chars].strip()


class ResearchAgent(BaseAgent):
    """Agent that performs automated company research using web retrieval, RAG grounding, and structured LLM extraction."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        reranker: Optional[Reranker] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = WEB_FETCH_TIMEOUT_SECONDS,
        max_web_chars: int = MAX_WEB_CONTENT_CHARS,
    ):
        """Initialize ResearchAgent.

        Args:
            llm_provider: LLM provider instance for completion.
            hybrid_retriever: Optional HybridRetriever for internal playbook / account grounding.
            reranker: Optional Reranker for prioritizing internal context chunks.
            http_client: Optional httpx.AsyncClient for web retrieval (useful for testing).
            timeout: Web fetch timeout in seconds.
            max_web_chars: Maximum characters to retain from web page content.
        """
        super().__init__(name="ResearchAgent")
        self.llm_provider = llm_provider or get_llm_provider()
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker
        self.http_client = http_client
        self.timeout = timeout
        self.max_web_chars = max_web_chars

    async def fetch_web_content(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Asynchronously fetch and extract visible text from a company URL.

        Args:
            url: Target website URL.

        Returns:
            Tuple of (extracted_text, error_message).
        """
        target_url = url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (GTM-Copilot-Bot/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            if self.http_client is not None:
                response = await self.http_client.get(target_url, headers=headers, timeout=self.timeout, follow_redirects=True)
            else:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(target_url, headers=headers)

            if response.status_code != 200:
                msg = f"HTTP {response.status_code} error when fetching {target_url}"
                logger.warning(msg)
                return None, msg

            extracted_text = extract_visible_text_from_html(response.text, max_chars=self.max_web_chars)
            return extracted_text, None

        except Exception as exc:
            msg = f"Failed to fetch {target_url}: {str(exc)}"
            logger.warning(msg)
            return None, msg

    async def retrieve_internal_context(self, company_name: Optional[str], url: Optional[str]) -> List[str]:
        """Query internal knowledge base for relevant playbook & account guidelines."""
        if not self.hybrid_retriever:
            return []

        search_terms = []
        if company_name:
            search_terms.append(company_name)
        if url:
            search_terms.append(url)
        search_terms.append("ICP criteria sales playbook value proposition industry")
        query = " ".join(search_terms)

        try:
            candidates = self.hybrid_retriever.retrieve(query=query, top_k=5)
            if self.reranker and candidates:
                candidates = self.reranker.rerank(query=query, chunks=candidates, top_k=3)
            return [chunk.text for chunk in candidates]
        except Exception as e:
            logger.warning("Internal retrieval failed in ResearchAgent: %s", e)
            return []

    def build_prompt(
        self,
        company_name: Optional[str],
        url: Optional[str],
        web_content: Optional[str],
        internal_context: List[str],
    ) -> str:
        """Construct the prompt sent to the LLM."""
        prompt_sections = [
            "### TARGET COMPANY DETAILS",
            f"- Specified Name: {company_name or 'Not explicitly provided'}",
            f"- Specified URL: {url or 'Not explicitly provided'}",
        ]

        if web_content:
            prompt_sections.append("\n### SOURCE 1: COMPANY WEBSITE CONTENT")
            prompt_sections.append(web_content)
        else:
            prompt_sections.append("\n### SOURCE 1: COMPANY WEBSITE CONTENT")
            prompt_sections.append("[Website content could not be retrieved]")

        if internal_context:
            prompt_sections.append("\n### SOURCE 2: INTERNAL PLAYBOOKS & RELEVANT CONTEXT")
            for idx, ctx in enumerate(internal_context, start=1):
                prompt_sections.append(f"\n[Context Chunk {idx}]\n{ctx}")

        prompt_sections.append(
            "\n### INSTRUCTION & OUTPUT SCHEMA\n"
            "Extract structured company facts and output valid, strictly-formatted JSON matching the following schema:\n"
            "{\n"
            '  "company_name": "Official company name",\n'
            '  "industry": "Primary industry classification",\n'
            '  "products_or_services": ["List of core platform products or services"],\n'
            '  "apparent_company_size_signals": "Signals regarding employee headcount, stage, ARR, or scale",\n'
            '  "recent_news_or_signals": ["Recent announcements, expansions, or leadership changes"],\n'
            '  "notable_tech_or_tools_mentioned": ["Technology stack components, tools, integrations"]\n'
            "}\n\n"
            "Guidelines:\n"
            "- Ground all facts strictly in the provided text.\n"
            "- If a piece of information is unknown or not mentioned in the source context, use null for single string fields or [] for lists. Do not hallucinate.\n"
            "- Return ONLY the JSON object without surrounding commentary."
        )

        return "\n".join(prompt_sections)

    async def run(self, input: ResearchInput) -> ResearchOutput:
        """Execute research workflow for the target company."""
        errors: List[str] = []
        source_urls: List[str] = []
        raw_context_used: List[str] = []

        web_text: Optional[str] = None
        if input.url:
            source_urls.append(input.url)
            web_text, fetch_err = await self.fetch_web_content(input.url)
            if fetch_err:
                errors.append(fetch_err)
            elif web_text:
                raw_context_used.append(f"[Web Content from {input.url}]: {web_text[:400]}...")

        # 2. Retrieve internal knowledge base context
        internal_chunks = await self.retrieve_internal_context(input.company_name, input.url)
        for chunk_text in internal_chunks:
            raw_context_used.append(f"[Internal Knowledge Base]: {chunk_text[:300]}...")

        # 3. Build prompt and query LLM
        prompt = self.build_prompt(
            company_name=input.company_name,
            url=input.url,
            web_content=web_text,
            internal_context=internal_chunks,
        )

        try:
            llm_response = await self.llm_provider.complete(prompt=prompt, system=SYSTEM_PROMPT)
        except Exception as e:
            err_msg = f"LLM completion error: {str(e)}"
            logger.error(err_msg)
            errors.append(err_msg)
            return ResearchOutput(
                company_name=input.company_name,
                source_urls=source_urls,
                raw_context_used=raw_context_used,
                errors=errors,
            )

        # 4. Parse structured JSON from LLM response
        try:
            parsed_data = extract_json(llm_response)
        except ValueError as e:
            err_msg = f"Failed to parse LLM JSON output: {str(e)}"
            logger.warning(err_msg)
            errors.append(err_msg)
            return ResearchOutput(
                company_name=input.company_name,
                source_urls=source_urls,
                raw_context_used=raw_context_used,
                errors=errors,
            )

        # Helper to ensure lists
        def ensure_list(val: Any) -> List[str]:
            if isinstance(val, list):
                return [str(item).strip() for item in val if str(item).strip()]
            if isinstance(val, str) and val.strip():
                return [val.strip()]
            return []

        return ResearchOutput(
            company_name=parsed_data.get("company_name") or input.company_name,
            industry=parsed_data.get("industry"),
            products_or_services=ensure_list(parsed_data.get("products_or_services")),
            apparent_company_size_signals=parsed_data.get("apparent_company_size_signals"),
            recent_news_or_signals=ensure_list(parsed_data.get("recent_news_or_signals")),
            notable_tech_or_tools_mentioned=ensure_list(parsed_data.get("notable_tech_or_tools_mentioned")),
            source_urls=source_urls,
            raw_context_used=raw_context_used,
            errors=errors,
        )
