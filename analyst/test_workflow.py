"""Offline functional tests of evidence boundaries, policy checks and CrewAI order."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from analyst.brief import extract_brief
from analyst.handoff import make_handoff
from analyst.schema import AnalystReport, CompanyBrief, COMPETITORS, FOCUSES
from analyst.validation import validate_report
from researcher.test_agent import pack, source
from researcher.schema import Citation


def evidence():
    return {"evidence_pack": pack().model_dump(), "sources": [source().model_dump()], "run": {"model": "fixture"}}


def brief():
    return CompanyBrief(
        company_name="Fizzera", source_filename="brief.pdf", pdf_sha256="fixture", text_sha256="fixture",
        pages=[{"page_number": 1, "text": "Ontario retail and accessible premium pricing."}],
        data_status_notes=["Company-provided assumptions."], investment_envelope_cad=1_200_000,
        product_launch_budget_cad=250_000,
    )


def report():
    return AnalystReport.model_validate({
        "company_name": "Fizzera", "research_question": pack().question, "as_of_date": "2026-10-16",
        "headline_insight_ids": ["i1"],
        "market_insights": [{"insight_id": "i1", "observed_fact": "Poppi announced a flavor.",
                             "evidence": {"finding_ids": ["f1"], "citations": []},
                             "interpretation_for_fizzera": "Test consumer interest before choosing a launch.",
                             "brief_pages": [1], "geographic_applicability": "Unspecified", "effectiveness_and_uncertainty": "No outcomes."}],
        "competitor_comparison": [{"company": c, "evidence_status": "covered" if c == "Poppi" else "no_evidence",
                                   "insight_ids": ["i1"] if c == "Poppi" else [], "evidence_gap": "Further evidence needed."}
                                  for c in COMPETITORS],
        "recommendations": [{"recommendation_id": f"r{i}", "focus": focus, "priority": "high", "decision_status": "needs_evidence",
                             "proposed_action": "Collect local evidence before deciding.", "rationale_for_fizzera": "Avoid unsupported expansion.",
                             "insight_ids": [], "brief_pages": [1], "success_measure": "Obtain a comparable local data sample.",
                             "uncertainty_and_next_evidence": "Local data missing.", "proposed_budget_cad": None,
                             "requires_additional_financing": False, "launch_concept": None}
                            for i, focus in enumerate(FOCUSES, 1)],
        "evidence_gaps": ["Canadian competitor pricing missing."], "limitations": ["Small sample."],
    })


class AnalystWorkflowTests(unittest.TestCase):
    def test_handoff_contains_full_sources_and_company_pages(self):
        original = evidence()
        payload, context = make_handoff(original, brief(), "2026-10-16")
        self.assertIn(source().paragraphs[0].text, context)
        self.assertIn("[BRIEF p1]", context)
        self.assertEqual(payload["researcher_output"], original)
        self.assertEqual(len(payload["handoff_sha256"]), 64)

    def test_bad_source_hash_stops_handoff(self):
        data = evidence()
        data["sources"][0]["paragraphs"][0]["text"] = "Edited after research"
        with self.assertRaisesRegex(ValueError, "hash"):
            make_handoff(data, brief(), "2026-10-16")

    def test_valid_analysis(self):
        validate_report(report(), evidence(), brief(), "2026-10-16")

    def test_brief_led_test_is_distinct_from_unsupported_strategic_recommendation(self):
        result = report()
        result.recommendations[2].decision_status = "propose_test"
        validate_report(result, evidence(), brief(), "2026-10-16")
        result.recommendations[2].decision_status = "recommend"
        with self.assertRaisesRegex(ValueError, "competitive evidence"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_unknown_finding_rejected(self):
        result = report()
        result.market_insights[0].evidence.finding_ids = ["invented"]
        with self.assertRaisesRegex(ValueError, "finding ID"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_unknown_paragraph_rejected(self):
        result = report()
        result.market_insights[0].evidence.citations = [Citation(article_id="a1", paragraph_id="invented")]
        with self.assertRaisesRegex(ValueError, "source paragraph"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_uncited_company_interpretation_rejected(self):
        result = report()
        result.market_insights[0].brief_pages = [99]
        with self.assertRaisesRegex(ValueError, "brief page"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_total_budget_ceiling(self):
        result = report()
        result.recommendations[0].proposed_budget_cad = 1_300_000
        with self.assertRaisesRegex(ValueError, "investment envelope"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_additional_financing_scenario_explicitly_allowed(self):
        result = report()
        result.recommendations[0].proposed_budget_cad = 1_300_000
        result.recommendations[0].requires_additional_financing = True
        validate_report(result, evidence(), brief(), "2026-10-16")

    def test_product_budget_ceiling(self):
        result = report()
        result.recommendations[2].proposed_budget_cad = 300_000
        with self.assertRaisesRegex(ValueError, "product launch budget"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_multiple_launches_rejected(self):
        result = report()
        result.recommendations[2].launch_concept = "Vanilla Cola"
        extra = result.recommendations[2].model_copy(update={"recommendation_id": "r6", "launch_concept": "Tropical Mango"})
        result.recommendations.append(extra)
        with self.assertRaisesRegex(ValueError, "one major launch"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_fabricated_competitor_coverage_rejected(self):
        result = report()
        result.competitor_comparison[-1].evidence_status = "covered"
        with self.assertRaisesRegex(ValueError, "no supporting insight"):
            validate_report(result, evidence(), brief(), "2026-10-16")

    def test_pdf_extraction_preserves_assumptions_and_limits(self):
        text = ("maximum discretionary strategic investment envelope of CAD $1.2 million. fictional research forecast.\f"
                "Maximum development and launch preparation budget: CAD $250,000.\fUnresolved question: When\f")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "brief.pdf"
            path.write_bytes(b"fixture-pdf")
            with patch("analyst.brief.shutil.which", return_value="pdftotext"), patch("analyst.brief.subprocess.run", return_value=SimpleNamespace(stdout=text)):
                result = extract_brief(path)
        self.assertEqual(len(result.pages), 3)
        self.assertEqual(result.investment_envelope_cad, 1_200_000)
        self.assertEqual(result.product_launch_budget_cad, 250_000)
        self.assertTrue(any("fictional" in n for n in result.data_status_notes))
        self.assertTrue(any("incomplete" in n for n in result.data_status_notes))

    def test_native_crewai_analyst_preserves_context_and_has_no_tools(self):
        from analyst.crew import build_analyst_crew
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            crew = build_analyst_crew()
        self.assertEqual(len(crew.tasks), 1)
        self.assertFalse(crew.agents[0].allow_delegation)
        self.assertFalse(crew.agents[0].respect_context_window)
        self.assertEqual(crew.agents[0].tools, [])
        self.assertEqual(crew.tasks[0].response_model, AnalystReport)

    def test_fresh_researcher_route_uses_existing_researcher_implementation(self):
        import json
        from analyst.workflow import ResearcherAnalystFlow
        with TemporaryDirectory() as folder:
            articles = Path(folder) / "articles.json"
            articles.write_text(json.dumps([source().model_dump()]))
            flow = ResearcherAnalystFlow(brief_path=Path("brief.pdf"), output_dir=Path(folder), as_of_date="2026-10-16", articles_path=articles)
            with patch("researcher.agent.research", return_value=evidence()) as researcher:
                result = flow.researcher_stage()
            researcher.assert_called_once()
            self.assertEqual(result["evidence_pack"], pack().model_dump())
            self.assertEqual(flow.state["researcher_mode"], "fresh_researcher_call")

    def test_real_flow_runs_handoff_before_analyst_without_rerunning_researcher(self):
        import json
        from analyst.workflow import ResearcherAnalystFlow
        events = []
        fake_output = SimpleNamespace(raw=report().model_dump_json(), pydantic=report(), token_usage=None)
        class FakeCrew:
            def kickoff(self, inputs):
                events.append("analyst")
                self_test.assertIn("[BRIEF p1]", inputs["handoff_context"])
                return fake_output
        self_test = self
        def checked_handoff(*args):
            events.append("handoff")
            return make_handoff(*args)
        with TemporaryDirectory() as folder:
            source_path = Path(folder) / "research.json"
            source_path.write_text(json.dumps(evidence()))
            output = Path(folder) / "output"
            output.mkdir()
            flow = ResearcherAnalystFlow(brief_path=Path("brief.pdf"), output_dir=output, as_of_date="2026-10-16", research_output_path=source_path)
            with patch("analyst.workflow.extract_brief", return_value=brief()), patch("analyst.workflow.make_handoff", side_effect=checked_handoff), patch("analyst.workflow.build_analyst_crew", return_value=FakeCrew()), patch("researcher.agent.research") as researcher:
                flow.kickoff()
            researcher.assert_not_called()
            self.assertEqual(events, ["handoff", "analyst"])
            self.assertTrue((output / "analyst_report.md").is_file())
            self.assertEqual(json.loads((output / "run_manifest.json").read_text())["researcher_mode"], "reuse_saved_output")


if __name__ == "__main__":
    unittest.main()
