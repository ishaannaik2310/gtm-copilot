"""Unit tests for AccountBriefOrchestrator."""

from typing import List, Optional
import pytest

from gtm_copilot.agents.base import BaseAgent
from gtm_copilot.models import (
    AccountBrief,
    FactCheckedBrief,
    FactCheckResult,
    ICPClassification,
    ResearchInput,
    ResearchOutput,
)
from gtm_copilot.orchestrator import AccountBriefOrchestrator, generate_account_brief


class MockResearchAgent(BaseAgent):
    """Mock ResearchAgent."""

    def __init__(self, research_output: Optional[ResearchOutput] = None):
        super().__init__(name="mock_research_agent")
        self.output = research_output or ResearchOutput(
            company_name="CloudScale Data Inc",
            industry="DevOps",
            products_or_services=["Kubernetes Observability"],
            apparent_company_size_signals="Series B stage, 220 employees",
            recent_news_or_signals=["Raised $42M"],
            notable_tech_or_tools_mentioned=["Kubernetes"],
            source_urls=["https://cloudscaledata.io"],
            raw_context_used=["[Web Content]: Observability platform."],
        )

    async def run(self, input: ResearchInput) -> ResearchOutput:
        return self.output


class MockICPClassifierAgent(BaseAgent):
    """Mock ICPClassifierAgent."""

    def __init__(self, icp_output: Optional[ICPClassification] = None):
        super().__init__(name="mock_icp_agent")
        self.output = icp_output or ICPClassification(
            fit_score=0.95,
            fit_label="strong_fit",
            rationale="Matches target Series B profile.",
            matched_criteria=["Series B", "DevOps"],
            mismatched_criteria=[],
        )

    async def run(self, input: ResearchOutput) -> ICPClassification:
        return self.output


class MockSynthesisAgent(BaseAgent):
    """Mock SynthesisAgent."""

    def __init__(self, should_fail: bool = False):
        super().__init__(name="mock_synthesis_agent")
        self.should_fail = should_fail

    async def run(self, research_output: ResearchOutput, icp_classification: Optional[ICPClassification] = None) -> AccountBrief:
        if self.should_fail:
            raise RuntimeError("Synthesis failed: LLM output could not be generated.")

        return AccountBrief(
            company_name=research_output.company_name or "CloudScale Data Inc",
            industry=research_output.industry,
            icp_classification=icp_classification or ICPClassification(fit_score=None, fit_label="unknown", rationale="N/A"),
            executive_summary="Synthesized executive summary for CloudScale Data Inc.",
            key_products_or_services=research_output.products_or_services,
            likely_pain_points=["Observability scale bottlenecks"],
            suggested_talk_tracks=["Talk track 1"],
            objection_handling_notes=["Objection 1"],
            source_urls=research_output.source_urls,
        )


class MockFactCheckAgent(BaseAgent):
    """Mock FactCheckAgent."""

    def __init__(self):
        super().__init__(name="mock_fact_check_agent")

    async def run(self, brief: AccountBrief, source_context: Optional[List[str]] = None) -> FactCheckedBrief:
        return FactCheckedBrief(
            brief=brief,
            fact_checks=[
                FactCheckResult(
                    claim="Synthesized executive summary for CloudScale Data Inc.",
                    supported=True,
                    supporting_evidence="Source context confirms business overview.",
                    confidence=0.95,
                )
            ],
            overall_faithfulness_score=1.0,
            flagged_claims=[],
        )


@pytest.mark.asyncio
async def test_orchestrator_full_chain_success():
    orchestrator = AccountBriefOrchestrator(
        research_agent=MockResearchAgent(),
        icp_agent=MockICPClassifierAgent(),
        synthesis_agent=MockSynthesisAgent(),
        fact_check_agent=MockFactCheckAgent(),
    )

    inp = ResearchInput(company_name="CloudScale", url="https://cloudscaledata.io")
    result = await orchestrator.run(inp)

    assert isinstance(result, FactCheckedBrief)
    assert result.brief.company_name == "CloudScale Data Inc"
    assert result.brief.icp_classification.fit_label == "strong_fit"
    assert result.overall_faithfulness_score == 1.0
    assert len(result.flagged_claims) == 0


@pytest.mark.asyncio
async def test_orchestrator_continues_when_icp_fails():
    # If ICP classifier fails, it returns fit_label='unknown', fit_score=None
    failed_icp = ICPClassification(
        fit_score=None,
        fit_label="unknown",
        rationale="ICP classification failed: API rate limit exceeded.",
        matched_criteria=[],
        mismatched_criteria=[],
    )

    orchestrator = AccountBriefOrchestrator(
        research_agent=MockResearchAgent(),
        icp_agent=MockICPClassifierAgent(icp_output=failed_icp),
        synthesis_agent=MockSynthesisAgent(),
        fact_check_agent=MockFactCheckAgent(),
    )

    inp = ResearchInput(company_name="CloudScale")
    result = await orchestrator.run(inp)

    # Pipeline should complete and brief should have unknown ICP
    assert isinstance(result, FactCheckedBrief)
    assert result.brief.icp_classification.fit_label == "unknown"
    assert result.brief.icp_classification.fit_score is None
    assert "rate limit" in result.brief.icp_classification.rationale


@pytest.mark.asyncio
async def test_orchestrator_halts_when_synthesis_fails():
    # If synthesis fails, pipeline must raise RuntimeError rather than creating fake brief
    orchestrator = AccountBriefOrchestrator(
        research_agent=MockResearchAgent(),
        icp_agent=MockICPClassifierAgent(),
        synthesis_agent=MockSynthesisAgent(should_fail=True),
        fact_check_agent=MockFactCheckAgent(),
    )

    inp = ResearchInput(company_name="CloudScale")
    with pytest.raises(RuntimeError, match="Synthesis failed"):
        await orchestrator.run(inp)
