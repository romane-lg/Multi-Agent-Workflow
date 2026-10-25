"""Offline presentation contracts and orchestration; no model quality judges."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import analyst
from executive.handoff import make_executive_input
from executive.render import render_html, render_markdown, safe_url
from executive.schema import ExecutiveBrief, TITLES
from executive.validation import validate_brief
from executive.workflow import ExecutiveOutputFlow
from reviewer.handoff import make_review_input
from reviewer.test_reviewer import assessment, save_analysis, with_issue
from reviewer.validation import finalize_review


def brief():
    return ExecutiveBrief.model_validate({
        "strategic_outlook": "Prioritize Ontario productivity and evidence gathering before committing to expansion.",
        "priority_focuses": ["ontario_retail", "pricing", "marketing"],
        "market_signals": [{"text": "Poppi announced a flavor; commercial outcomes are not established.", "insight_ids": ["i1"]},
                           {"text": "This sample offers limited competitor coverage, limiting comparison.", "insight_ids": ["i1"]}],
        "topics": {focus: {"implication": "Local evidence is needed before committing.",
                           "action": "Collect local evidence before deciding.",
                           "metric_or_gate": "Obtain a comparable local data sample.",
                           "caveat": "Existing evidence does not establish Canadian demand."} for focus in TITLES},
    })


class ExecutiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.analysis, self.review = self.root / "analysis", self.root / "review"
        self.analysis.mkdir()
        self.review.mkdir()
        save_analysis(self.analysis)
        self.save_review()

    def save_review(self, blocked=True):
        payload, _ = make_review_input(self.analysis)
        result = finalize_review(with_issue() if blocked else assessment(), payload, {})
        (self.review / "review_input.json").write_text(json.dumps(payload))
        (self.review / "review_report.json").write_text(result.model_dump_json())

    def inputs(self):
        return make_executive_input(self.analysis, self.review)[0]

    def test_hold_cannot_become_approval(self):
        payload = self.inputs()
        self.assertEqual(payload["publication_status"], "hold_for_human_review")
        for renderer in (render_markdown, render_html):
            text = renderer(brief(), payload)
            self.assertIn("pending human review", text)
            self.assertNotIn("Model review completed", text)

    def test_pass_keeps_management_proposal_label(self):
        self.save_review(blocked=False)
        payload = self.inputs()
        self.assertEqual(payload["publication_status"], "review_passed")
        self.assertIn("management proposals", render_html(brief(), payload))

    def test_changed_draft_rejects_old_review(self):
        path = self.analysis / "analyst_report.json"
        data = json.loads(path.read_text())
        data["limitations"].append("Changed")
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "exact analysis"):
            self.inputs()

    def test_inconsistent_review_verdict_rejected(self):
        path = self.review / "review_report.json"
        data = json.loads(path.read_text())
        data["overall_verdict"] = "pass"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            self.inputs()

    def test_source_corruption_rejected(self):
        path = self.analysis / "handoff.json"
        data = json.loads(path.read_text())
        data["researcher_output"]["sources"][0]["paragraphs"][0]["text"] = "Changed source"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "hash"):
            self.inputs()

    def test_word_caps_and_citations(self):
        payload = self.inputs()
        validate_brief(brief(), payload)
        value = brief()
        value.market_signals[0].insight_ids = ["invented"]
        with self.assertRaisesRegex(ValueError, "known"):
            validate_brief(value, payload)
        value = brief()
        value.strategic_outlook = "word " * 81
        with self.assertRaisesRegex(ValueError, "80 words"):
            validate_brief(value, payload)

    def test_priorities_and_topic_coverage(self):
        value = brief()
        value.priority_focuses = ["pricing", "marketing", "bc_expansion"]
        with self.assertRaisesRegex(ValueError, "Ontario"):
            validate_brief(value, self.inputs())
        data = brief().model_dump()
        del data["topics"]["marketing"]
        with self.assertRaises(ValueError):
            ExecutiveBrief.model_validate(data)

    def test_market_metrics_and_causal_success_language_rejected(self):
        payload = self.inputs()
        value = brief()
        value.market_signals[0].text = "A partnership produced a 200% sales boost."
        with self.assertRaisesRegex(ValueError, "qualitative"):
            validate_brief(value, payload)
        value = brief()
        value.topics.marketing.implication = "Influencer marketing has proven effective."
        with self.assertRaisesRegex(ValueError, "association"):
            validate_brief(value, payload)

    def test_html_escapes_generated_markup(self):
        value = brief()
        value.strategic_outlook = '<script>alert("test")</script>'
        html = render_html(value, self.inputs())
        self.assertNotIn('<script>alert', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertEqual(safe_url("javascript:alert(1)"), "#")

    def test_source_links_and_decision_status_are_code_derived(self):
        payload = self.inputs()
        html = render_html(brief(), payload)
        self.assertIn("Evidence needed", html)
        self.assertIn("Company brief pp. 1", html)
        self.assertIn('id="source-1"', html)
        self.assertIn("Evidence gaps:", html)
        for title in TITLES.values():
            self.assertIn(title.replace("&", "&amp;"), html)

    def test_flow_writes_both_formats_without_modifying_upstream(self):
        before = {str(p): p.read_bytes() for root in (self.analysis, self.review) for p in root.iterdir()}
        value = brief()
        output = SimpleNamespace(raw=value.model_dump_json(), pydantic=value, token_usage=None)
        crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model="fixture"))],
                               kickoff=lambda **kw: output)
        target = self.root / "executive"
        with patch("executive.workflow.build_executive_crew", return_value=crew), patch('executive.audit.audit_executive', return_value={'passed': True}):
            result = ExecutiveOutputFlow(analysis_run=self.analysis, review_dir=self.review, output_dir=target).kickoff()
        self.assertEqual(result["presentation_status"], "completed")
        self.assertEqual(result["publication_status"], "hold_for_human_review")
        for name in ("executive_brief.html", "executive_brief.md", "executive_brief.json", "executive_input.json", "executive_manifest.json"):
            self.assertTrue((target / name).is_file())
        self.assertEqual(before, {str(p): p.read_bytes() for root in (self.analysis, self.review) for p in root.iterdir()})

    def test_native_agent_has_no_research_tools_or_delegation(self):
        from executive.crew import build_executive_crew
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-not-a-real-key"}):
            crew = build_executive_crew()
        self.assertFalse(crew.agents[0].tools)
        self.assertFalse(crew.agents[0].allow_delegation)
        self.assertEqual(crew.agents[0].max_iter, 1)
        self.assertFalse(crew.memory)

    def test_failed_final_prose_audit_holds_an_upstream_pass(self):
        self.save_review(blocked=False)
        value = brief()
        output = SimpleNamespace(raw=value.model_dump_json(), pydantic=value, token_usage=None)
        crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model='fixture'))], kickoff=lambda **kw: output)
        with patch('executive.workflow.build_executive_crew', return_value=crew), patch('executive.audit.audit_executive', return_value={'passed': False}):
            result = ExecutiveOutputFlow(analysis_run=self.analysis, review_dir=self.review, output_dir=self.root/'held_editor').kickoff()
        self.assertEqual(result['publication_status'], 'hold_for_human_review')
        self.assertIn('pending human review', (self.root/'held_editor/executive_brief.html').read_text())

    def test_editorial_audit_cannot_invent_source_excerpts(self):
        from executive.audit import editorial_fields, validate_audit
        payload = self.inputs()
        checks = {key: {'verdict': 'supported', 'explanation': 'Transport fixture.',
                  'source_anchors': [{'article_id': 'a1', 'paragraph_id': 'p1', 'excerpt': 'Invented unsupported quotation.'}],
                  'brief_anchors': [], 'required_correction': ''} for key in editorial_fields(brief())}
        with self.assertRaisesRegex(ValueError, 'excerpt'):
            validate_audit(checks, brief(), payload)

    def test_saved_executive_response_finalizes_without_a_model_call(self):
        from executive.workflow import finalize_saved_executive
        target = self.root/'saved_executive'
        target.mkdir()
        payload = self.inputs()
        (target/'executive_input.json').write_text(json.dumps(payload))
        value = brief()
        value.topics.bc_expansion.caveat = 'BC evidence is still incomplete and requires a local check before any expansion commitment is considered by the Fizzera management team.'
        (target/'executive_raw.txt').write_text(value.model_dump_json())
        with patch('executive.workflow.build_executive_crew',side_effect=AssertionError('Must not call a model')):
            result = finalize_saved_executive(analysis_run=self.analysis,review_dir=self.review,output_dir=target,model='fixture')
        self.assertFalse(result['model_call_repeated'])
        self.assertEqual(result['publication_status'],'hold_for_human_review')
        self.assertTrue((target/'executive_brief.html').exists())

    def test_integrated_flow_places_executive_after_review(self):
        from analyst.workflow import run_workflow
        from analyst.test_workflow import evidence, report
        from reviewer.test_reviewer import company_brief
        events = []
        analysis_report = report()
        analyst_crew = SimpleNamespace(kickoff=lambda **kw: events.append("analyst") or SimpleNamespace(
            raw=analysis_report.model_dump_json(), pydantic=analysis_report, token_usage=None))
        from reviewer.test_reviewer import live_response
        review_assessment = with_issue()
        review_crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model="fixture"))],
            tasks=[SimpleNamespace(description="Fixture instructions")],
            kickoff=lambda **kw: events.append("reviewer") or SimpleNamespace(
                raw=json.dumps(live_response(review_assessment)), pydantic=None, token_usage=None))
        value = brief()
        executive_crew = SimpleNamespace(agents=[SimpleNamespace(llm=SimpleNamespace(model="fixture"))],
            kickoff=lambda **kw: events.append("executive") or SimpleNamespace(
                raw=value.model_dump_json(), pydantic=value, token_usage=None))
        source = self.root / "research.json"
        source.write_text(json.dumps(evidence()))
        target = self.root / "integrated"
        target.mkdir()
        with patch("analyst.workflow.extract_brief", return_value=company_brief()), patch("analyst.workflow.build_analyst_crew", return_value=analyst_crew), patch("reviewer.service.build_reviewer_crew", return_value=review_crew), patch("executive.workflow.build_executive_crew", return_value=executive_crew), patch('executive.audit.audit_executive', return_value={'passed': True}):
            result = run_workflow.__wrapped__(executive=True, brief_path=Path("brief.pdf"), output_dir=target,
                                              as_of_date="2026-10-16", research_output_path=source)
        self.assertEqual(events, ["analyst", "reviewer", "executive"])
        self.assertEqual(result["presentation_status"], "completed")
        self.assertEqual(result["publication_status"], "hold_for_human_review")
        self.assertTrue((target / "executive" / "executive_brief.html").is_file())
        self.assertTrue(json.loads((target / "run_manifest.json").read_text())["executive_run"])


if __name__ == "__main__":
    unittest.main()
