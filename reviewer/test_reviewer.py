"""Offline contract and orchestration checks; no quality judges or model calls."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from analyst.handoff import make_handoff
from analyst.test_workflow import brief, evidence, report
from reviewer.handoff import make_review_input
from reviewer.schema import CRITERIA, ReviewAssessment, ReviewIssue, build_review_response_model, item_slots, normalize_assessment
from reviewer.validation import expected_targets, finalize_review


def company_brief():
    value = brief()
    text = "\n\f\n".join(p.text for p in value.pages)
    return value.model_copy(update={"text_sha256": hashlib.sha256(text.encode()).hexdigest()})


def inputs():
    handoff, _ = make_handoff(evidence(), company_brief(), "2026-10-16")
    return {
        "analyst_report": report().model_dump(), "upstream_handoff": handoff,
        "structural_preflight_error": None,
        "input_hashes": {"analyst_report_sha256": "fixture", "upstream_handoff_sha256": handoff["handoff_sha256"]},
    }


def assessment():
    targets = expected_targets(inputs())
    return ReviewAssessment.model_validate({
        "criteria": [{"criterion": c, "explanation": "Checked against the frozen inputs.", "issue_ids": []} for c in CRITERIA],
        "reviewed_items": [{"target_type": kind, "target_id": item_id, "disposition": "supported", "issue_ids": []}
                           for kind, ids in targets.items() for item_id in sorted(ids)],
        "issues": [], "limitations": ["Model review is not ground truth."],
    })


def with_issue(*, severity="blocking", report_level=False):
    result = assessment()
    issue = ReviewIssue(
        issue_id="issue_1", severity=severity, criterion="source_support", category="citation_mismatch",
        target_type="report" if report_level else "market_insight", target_ids=[] if report_level else ["i1"],
        problem="The cited paragraph does not support the stated numerical outcome.",
        evidence={"finding_ids": ["f1"], "citations": [{"article_id": "a1", "paragraph_id": "p1"}]},
        brief_pages=[], required_correction="Remove the unsupported number or supply directly supporting evidence.",
    )
    result.issues.append(issue)
    result.criteria[0].issue_ids = [issue.issue_id]
    if not report_level:
        item = next(i for i in result.reviewed_items if i.target_type == "market_insight")
        item.issue_ids = [issue.issue_id]
        item.disposition = "needs_correction" if severity == "blocking" else "qualified"
    return result


def save_analysis(folder: Path):
    data = inputs()
    (folder / "handoff.json").write_text(json.dumps(data["upstream_handoff"]))
    (folder / "analyst_report.json").write_text(json.dumps(data["analyst_report"]))


class ReviewerTests(unittest.TestCase):
    def test_no_blocking_issues_passes(self):
        result = finalize_review(assessment(), inputs(), {})
        self.assertEqual(result.overall_verdict, "pass")
        self.assertEqual(result.publication_status, "review_passed")

    def test_blocking_issue_holds_output(self):
        result = finalize_review(with_issue(), inputs(), {})
        self.assertEqual(result.overall_verdict, "fail")
        self.assertEqual(result.criterion_verdicts["source_support"], "fail")
        self.assertEqual(result.publication_status, "hold_for_human_review")

    def test_advisory_alone_does_not_fail(self):
        self.assertEqual(finalize_review(with_issue(severity="advisory"), inputs(), {}).overall_verdict, "pass")

    def test_missing_reviewed_item_rejected(self):
        value = assessment()
        value.reviewed_items.pop()
        with self.assertRaisesRegex(ValueError, "every Analyst"):
            finalize_review(value, inputs(), {})

    def test_omitted_criterion_rejected(self):
        value = assessment()
        value.criteria.pop()
        with self.assertRaisesRegex(ValueError, "four criteria"):
            finalize_review(value, inputs(), {})

    def test_issue_cannot_cite_invented_source(self):
        value = with_issue()
        value.issues[0].evidence.citations[0].paragraph_id = "nonexistent"
        with self.assertRaisesRegex(ValueError, "source paragraph"):
            finalize_review(value, inputs(), {})

    def test_issue_cannot_cite_invented_brief_page(self):
        value = with_issue()
        value.issues[0].brief_pages = [99]
        with self.assertRaisesRegex(ValueError, "brief page"):
            finalize_review(value, inputs(), {})

    def test_issue_must_target_an_existing_item(self):
        value = with_issue()
        value.issues[0].target_ids = ["nonexistent"]
        with self.assertRaisesRegex(ValueError, "Analyst target"):
            finalize_review(value, inputs(), {})

    def test_support_label_cannot_hide_blocking_issue(self):
        value = with_issue()
        next(i for i in value.reviewed_items if i.target_type == "market_insight").disposition = "supported"
        with self.assertRaisesRegex(ValueError, "disposition"):
            finalize_review(value, inputs(), {})

    def test_criterion_must_link_its_issues(self):
        value = with_issue()
        value.criteria[0].issue_ids = []
        with self.assertRaisesRegex(ValueError, "Criterion"):
            finalize_review(value, inputs(), {})

    def test_preflight_error_cannot_be_approved(self):
        data = inputs()
        data["structural_preflight_error"] = "Unknown Researcher finding ID"
        with self.assertRaisesRegex(ValueError, "preflight failure"):
            finalize_review(assessment(), data, {})
        value = with_issue(report_level=True)
        value.issues[0].category = "structural"
        self.assertEqual(finalize_review(value, data, {}).overall_verdict, "fail")

    def test_handoff_retains_complete_sources_and_brief(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            save_analysis(path)
            data, context = make_review_input(path)
        self.assertIn(evidence()["sources"][0]["paragraphs"][0]["text"], context)
        self.assertIn("[BRIEF p1]", context)
        self.assertIsNone(data["structural_preflight_error"])

    def test_corrupt_upstream_handoff_stops_before_review(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            save_analysis(path)
            data = json.loads((path / "handoff.json").read_text())
            data["handoff_sha256"] = "modified"
            (path / "handoff.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "handoff hash"):
                make_review_input(path)

    def test_bad_analyst_references_are_reviewable_not_silently_approved(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            save_analysis(path)
            data = json.loads((path / "analyst_report.json").read_text())
            data["market_insights"][0]["evidence"]["finding_ids"] = ["invented"]
            (path / "analyst_report.json").write_text(json.dumps(data))
            payload, _ = make_review_input(path)
        self.assertIn("Unknown Researcher finding", payload["structural_preflight_error"])

    def test_native_reviewer_has_separate_agent_and_no_correction_tools(self):
        from reviewer.crew import build_reviewer_crew
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            crew = build_reviewer_crew(inputs())
        self.assertEqual(len(crew.agents), 1)
        self.assertEqual(crew.agents[0].role, "Independent Fizzera Evidence Reviewer")
        self.assertEqual(crew.agents[0].tools, [])
        self.assertFalse(crew.agents[0].allow_delegation)
        self.assertFalse(crew.agents[0].respect_context_window)
        self.assertEqual(crew.tasks[0].guardrail_max_retries, 0)

    def test_response_schema_requires_recommendation_checks(self):
        from pydantic import ValidationError
        data = {"criteria": {c: "Checked the original evidence." for c in CRITERIA}, "report_issues": [], "limitations": [],
                "item_reviews": {slot: {"explanation": "Supported in the supplied context.", "issues": []} for slot in item_slots(inputs())}}
        model = build_review_response_model(inputs())
        parsed = model.model_validate(data)
        normalized = normalize_assessment(parsed.model_dump(), inputs())
        self.assertEqual(len(normalized.reviewed_items), 12)
        missing = next(slot for slot, (kind, _) in item_slots(inputs()).items() if kind == "recommendation")
        del data["item_reviews"][missing]
        with self.assertRaises(ValidationError):
            model.model_validate(data)

    def test_issue_targets_and_dispositions_are_attached_consistently_in_code(self):
        local_issue = with_issue().issues[0].model_dump(exclude={"issue_id", "target_type", "target_ids"})
        generated = {"criteria": {c: "Checked the original evidence." for c in CRITERIA}, "report_issues": [], "limitations": [],
                     "item_reviews": {slot: {"explanation": "Checked against source paragraphs.", "issues": []} for slot in item_slots(inputs())}}
        generated["item_reviews"]["check_001"]["issues"] = [local_issue]
        normalized = normalize_assessment(generated, inputs())
        self.assertEqual(normalized.issues[0].target_ids, ["i1"])
        self.assertEqual(normalized.reviewed_items[0].disposition, "needs_correction")
        self.assertEqual(finalize_review(normalized, inputs(), {}).overall_verdict, "fail")

    def test_saved_review_never_reruns_or_modifies_upstream_agents(self):
        from reviewer.workflow import SavedAnalysisReviewFlow
        value = assessment()
        fake = SimpleNamespace(raw=value.model_dump_json(), pydantic=value, token_usage=None)
        crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model="fixture"))],
                               tasks=[SimpleNamespace(description="Fixture review instructions")])
        from unittest.mock import Mock
        crew.kickoff = Mock(return_value=fake)
        with TemporaryDirectory() as folder:
            source = Path(folder) / "analyst"
            source.mkdir()
            save_analysis(source)
            original = {p.name: p.read_bytes() for p in source.iterdir()}
            target = Path(folder) / "review"
            with patch("reviewer.service.build_reviewer_crew", return_value=crew), patch("researcher.agent.research") as researcher, patch("analyst.workflow.build_analyst_crew") as analyst:
                result = SavedAnalysisReviewFlow(analysis_run=source, output_dir=target).kickoff()
            researcher.assert_not_called()
            analyst.assert_not_called()
            crew.kickoff.assert_called_once()
            self.assertEqual(result["overall_verdict"], "pass")
            self.assertEqual({p.name: p.read_bytes() for p in source.iterdir()}, original)
            self.assertTrue((target / "review_report.md").is_file())

    def test_full_crewai_flow_orders_reviewer_after_analyst(self):
        from analyst.workflow import run_workflow
        events = []
        fake_analyst = SimpleNamespace(raw=report().model_dump_json(), pydantic=report(), token_usage=None)
        value = with_issue()
        fake_review = SimpleNamespace(raw=value.model_dump_json(), pydantic=value, token_usage=None)
        from unittest.mock import Mock
        analyst_crew = SimpleNamespace(kickoff=Mock(side_effect=lambda **kwargs: events.append("analyst") or fake_analyst))
        reviewer_crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model="fixture"))],
                                        tasks=[SimpleNamespace(description="Fixture review instructions")],
                                       kickoff=Mock(side_effect=lambda **kwargs: events.append("reviewer") or fake_review))
        with TemporaryDirectory() as folder:
            source = Path(folder) / "research.json"
            source.write_text(json.dumps(evidence()))
            output = Path(folder) / "run"
            output.mkdir()
            with patch("analyst.workflow.extract_brief", return_value=company_brief()), patch("analyst.workflow.build_analyst_crew", return_value=analyst_crew), patch("reviewer.service.build_reviewer_crew", return_value=reviewer_crew):
                result = run_workflow.__wrapped__(review=True, brief_path=Path("brief.pdf"), output_dir=output,
                                                 as_of_date="2026-10-16", research_output_path=source)
            self.assertEqual(events, ["analyst", "reviewer"])
            self.assertEqual(result["overall_verdict"], "fail")
            self.assertEqual(json.loads((output / "run_manifest.json").read_text())["publication_status"], "hold_for_human_review")
            analyst_crew.kickoff.assert_called_once()
            reviewer_crew.kickoff.assert_called_once()

    def test_invalid_review_keeps_integrated_draft_pending(self):
        from analyst.workflow import run_workflow
        from unittest.mock import Mock
        fake_analyst = SimpleNamespace(raw=report().model_dump_json(), pydantic=report(), token_usage=None)
        analyst_crew = SimpleNamespace(kickoff=Mock(return_value=fake_analyst))
        with TemporaryDirectory() as folder:
            source = Path(folder) / "research.json"
            source.write_text(json.dumps(evidence()))
            output = Path(folder) / "run"
            output.mkdir()
            with patch("analyst.workflow.extract_brief", return_value=company_brief()), patch("analyst.workflow.build_analyst_crew", return_value=analyst_crew), patch("reviewer.workflow.perform_review", side_effect=ValueError("Invalid Reviewer response")):
                with self.assertRaisesRegex(ValueError, "Invalid Reviewer"):
                    run_workflow.__wrapped__(review=True, brief_path=Path("brief.pdf"), output_dir=output,
                                             as_of_date="2026-10-16", research_output_path=source)
            manifest = json.loads((output / "run_manifest.json").read_text())
            self.assertEqual(manifest["publication_status"], "pending_review")
            self.assertFalse((output / "review" / "review_report.json").exists())


if __name__ == "__main__":
    unittest.main()
