"""Offline correction-loop contracts; no model calls or quality scoring."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from analyst.revision import AnalystRevisionFlow, prepare_revision, revision_response_model, validate_revision, recheck_revision
from reviewer.handoff import make_review_input
from reviewer.schema import build_review_response_model
from reviewer.test_reviewer import save_analysis, with_issue
from reviewer.validation import finalize_review


def save_review(analysis, review):
    payload, _ = make_review_input(analysis)
    result = finalize_review(with_issue(), payload, {})
    (review / "review_input.json").write_text(json.dumps(payload))
    (review / "review_report.json").write_text(result.model_dump_json())


def response(frozen):
    return {"report": copy.deepcopy(frozen["original_review_input"]["analyst_report"]),
            "feedback_responses": {i["issue_id"]: {
                "disposition": "declined", "rationale": "The original paragraph supports the claim.",
                "change_description": "No change; original evidence retained."}
                for i in frozen["selected_issues"]}}


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.analysis, self.review = self.root / "original", self.root / "review"
        self.analysis.mkdir()
        self.review.mkdir()
        save_analysis(self.analysis)
        save_review(self.analysis, self.review)

    def prepared(self):
        return prepare_revision(self.analysis, self.review, ["issue_1"])[0]

    def test_exact_draft_feedback_binding(self):
        data = json.loads((self.analysis / "analyst_report.json").read_text())
        data["limitations"].append("Changed since review")
        (self.analysis / "analyst_report.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "exact Analyst"):
            self.prepared()

    def test_inconsistent_saved_verdict_rejected(self):
        path = self.review / "review_report.json"
        data = json.loads(path.read_text())
        data["overall_verdict"] = "pass"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            self.prepared()

    def test_unknown_duplicate_or_empty_selection_rejected(self):
        for ids in ([], ["missing"], ["issue_1", "issue_1"]):
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, "Select"):
                prepare_revision(self.analysis, self.review, ids)

    def test_second_cycle_rejected(self):
        (self.analysis / "revision_lineage.json").write_text('{"correction_attempt": 1}')
        with self.assertRaisesRegex(ValueError, "Maximum one"):
            self.prepared()

    def test_every_selected_issue_requires_response(self):
        frozen = self.prepared()
        data = response(frozen)
        data["feedback_responses"] = {}
        with self.assertRaises(ValueError):
            validate_revision(data, frozen)

    def test_declining_feedback_is_allowed_with_explanation(self):
        frozen = self.prepared()
        result = validate_revision(response(frozen), frozen)
        self.assertEqual(result.feedback_responses.issue_1.disposition, "declined")

    def test_new_source_citation_is_rejected(self):
        frozen = self.prepared()
        data = response(frozen)
        data["report"]["market_insights"][0]["evidence"]["citations"] = [{"article_id": "a1", "paragraph_id": "invented"}]
        with self.assertRaisesRegex(ValueError, "Unknown or unavailable"):
            validate_revision(data, frozen)

    def test_preserves_insight_identity(self):
        frozen = self.prepared()
        data = response(frozen)
        data["report"]["market_insights"].append({**data["report"]["market_insights"][0], "insight_id": "extra"})
        with self.assertRaisesRegex(ValueError, "preserve insight"):
            validate_revision(data, frozen)

    def test_recheck_schema_requires_each_feedback_resolution(self):
        payload, _ = make_review_input(self.analysis)
        base = build_review_response_model(payload)
        self.assertNotIn("feedback_resolution", base.model_fields)
        payload["revision_feedback"] = {"selected_issues": self.prepared()["selected_issues"]}
        schema = build_review_response_model(payload)
        self.assertIn("feedback_resolution", schema.model_fields)
        self.assertIn("issue_1", schema.model_fields["feedback_resolution"].annotation.model_fields)

    def test_flow_revises_then_rechecks_preserving_original(self):
        before = {p.name: p.read_bytes() for p in self.analysis.iterdir()}
        frozen = self.prepared()
        parsed = revision_response_model(frozen["selected_issues"]).model_validate(response(frozen))
        output = SimpleNamespace(raw=parsed.model_dump_json(), pydantic=parsed, token_usage=None)
        crew = SimpleNamespace(kickoff=lambda **kw: output,
                               agents=[SimpleNamespace(llm=SimpleNamespace(model="mock"))])
        target = self.root / "revision"
        captured = []
        def recheck(payload, context, directory):
            captured.append(payload)
            self.assertTrue((target / "revision_changes.json").is_file())
            self.assertEqual(payload["revision_feedback"]["analyst_responses"]["issue_1"]["disposition"], "declined")
            return {"overall_verdict": "pass", "publication_status": "review_passed", "run": {
                "feedback_resolution": {"issue_1": {"status": "disputed", "explanation": "Needs human review"}}}}
        with patch("analyst.revision.build_revision_crew", return_value=crew), patch("analyst.revision.perform_review", side_effect=recheck):
            result = AnalystRevisionFlow(analysis_run=self.analysis, review_dir=self.review,
                                        output_dir=target, issue_ids=["issue_1"]).kickoff()
        self.assertEqual(len(captured), 1)
        self.assertEqual(result["publication_status"], "hold_for_human_review")
        self.assertEqual(result["unresolved_blocking_feedback"], ["issue_1"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.analysis.iterdir()})
        with self.assertRaisesRegex(ValueError, "Maximum one"):
            prepare_revision(target, self.review, ["issue_1"])

    def test_failed_recheck_leaves_pending_state(self):
        frozen = self.prepared()
        parsed = revision_response_model(frozen["selected_issues"]).model_validate(response(frozen))
        output = SimpleNamespace(raw=parsed.model_dump_json(), pydantic=parsed, token_usage=None)
        crew = SimpleNamespace(kickoff=lambda **kw: output,
                               agents=[SimpleNamespace(llm=SimpleNamespace(model="mock"))])
        target = self.root / "revision"
        with patch("analyst.revision.build_revision_crew", return_value=crew), patch("analyst.revision.perform_review", side_effect=RuntimeError("failed recheck")):
            with self.assertRaisesRegex(RuntimeError, "failed recheck"):
                AnalystRevisionFlow(analysis_run=self.analysis, review_dir=self.review,
                                    output_dir=target, issue_ids=["issue_1"]).kickoff()
        manifest = json.loads((target / "revision_manifest.json").read_text())
        self.assertEqual(manifest["publication_status"], "pending_review")

        # A transport retry uses the saved revision, never another Analyst call.
        with patch("analyst.revision.build_revision_crew", side_effect=AssertionError("Analyst must not rerun")), patch("analyst.revision.perform_review", return_value={
            "overall_verdict": "pass", "publication_status": "review_passed", "run": {
                "feedback_resolution": {"issue_1": {"status": "resolved", "explanation": "Original claim supported"}}}}):
            result = recheck_revision(target, target / "retry")
        self.assertEqual(result["publication_status"], "review_passed")

        data = json.loads((target / "analyst_report.json").read_text())
        data["limitations"].append("Tampered after revision")
        (target / "analyst_report.json").write_text(json.dumps(data))
        with patch("analyst.revision.perform_review", side_effect=AssertionError("Must validate before model call")):
            with self.assertRaisesRegex(ValueError, "report hash mismatch"):
                recheck_revision(target, target / "retry_again")


if __name__ == "__main__":
    unittest.main()
