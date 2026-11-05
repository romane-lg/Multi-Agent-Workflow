"""Offline integration tests with fictitious evidence; no SDK/network required."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from intelligence.schema import Query, ResearchPlan, ResearchBatch, AnalystReport, ReviewAssessment
from intelligence.runtime import StageResult
from intelligence.workflow import run_workflow
from planner.agent import validate_plan
from researcher.general import validate_sources, validate_batch
from analyst.general import validate_report
from reviewer.general import validate_review

QUERY = {"question": "Compare Acme and Beacon product features.",
         "companies": ["Acme", "Beacon"], "as_of_date": "2026-11-04"}
RISKS = [{"criterion": k, "status": "clear", "explanation": "Checked against fixture evidence."}
         for k in ("chronology", "geography", "causality", "company_constraints")]

def sources(count=1, unavailable=0):
    result = []
    for i in range(count):
        text = f"{QUERY['companies'][0]} announced fixture feature number {i}."
        missing = i < unavailable
        body = "" if missing else text
        result.append({"article_id": f"a{i}", "title": "Fictitious unit-test source",
            "url": f"https://example.com/fixture/{i}", "publication_date": "2026-01-01",
            "availability": "unavailable" if missing else "full_text",
            "access_note": "Synthetic test fixture, not market evidence.",
            "text_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "paragraphs": [] if missing else [{"paragraph_id": "p1", "text": body}]})
    return result

def plan():
    return {"question": QUERY["question"], "companies": QUERY["companies"],
        "as_of_date": QUERY["as_of_date"], "period": None,
        "tasks": [{"task_id": "t1", "question": QUERY["question"], "dimension": "features",
            "evidence_requirements": ["Published features with attribution"],
            "preferred_source_types": ["Official product pages"],
            "suggested_search_queries": ["Acme Beacon product features"],
            "completion_criteria": ["Compare supported features or identify gaps"]}],
        "limitations": ["Only frozen source text can be inspected."]}

class FakeBackend:
    def __init__(self, mutate=None):
        self.calls = []
        self.mutate = mutate

    def generate(self, stage, schema, instructions, payload):
        self.calls.append(stage)
        if stage == "planner":
            data = plan()
        elif stage == "researcher":
            data = {"article_assessments": [], "findings": [], "limitations": []}
            for a in payload["articles"]:
                data["article_assessments"].append({"article_id": a["article_id"], "relevance": "high",
                    "summary": "Fixture announcement.", "reason": "Relevant fixture evidence."})
                data["findings"].append({"finding_id": a["article_id"], "claim": a["paragraphs"][0]["text"],
                    "publication_date": a["publication_date"], "companies": [payload["plan"]["companies"][0]], "dimension": "features",
                    "task_ids": ["t1"], "attribution": "Fixture source", "effectiveness": "not_measured",
                    "limitations": "Announcement does not establish outcomes.",
                    "citations": [{"article_id": a["article_id"], "paragraph_id": "p1"}]})
        elif stage == "analyst":
            evidence = payload["evidence"]
            fs = evidence["findings"]
            data = {"question": QUERY["question"], "companies": QUERY["companies"],
                "as_of_date": QUERY["as_of_date"], "headline_insight_ids": ["i1"] if fs else [],
                "insights": [{"insight_id": "i1", "task_ids": ["t1"], "observed_fact": fs[0]["claim"],
                    "interpretation": "An announced feature; Beacon remains a gap.",
                    "evidence": {"finding_ids": [fs[0]["finding_id"]], "citations": []},
                    "context_keys": [], "uncertainty": "No measured outcomes."}] if fs else [],
                "recommendations": [],
                "answer_components": [{"task_id": "t1", "insight_ids": ["i1"] if fs else [],
                                       "gap": "Beacon has no source evidence."}],
                "limitations": ["Synthetic fixtures only."]}
        else:
            report = payload["analyst_report"]
            data = {"items": [], "blocking_issues": [], "limitations": ["Model review is provisional."]}
            for i in report["insights"]:
                a = next(a for a in payload["evidence"]["sources"] if a["availability"] == "full_text")
                data["items"].append({"target_type": "insight", "target_id": i["insight_id"],
                    "disposition": "supported", "explanation": "Matches the fixture paragraph.",
                    "anchors": [{"article_id": a["article_id"], "paragraph_id": "p1",
                                 "excerpt": a["paragraphs"][0]["text"]}],
                    "risks": copy.deepcopy(RISKS), "required_correction": ""})
            for t in report["answer_components"]:
                data["items"].append({"target_type": "task", "target_id": t["task_id"],
                    "disposition": "gap_acknowledged", "explanation": "Missing company acknowledged.",
                    "anchors": [], "risks": copy.deepcopy(RISKS), "required_correction": ""})
        if self.mutate:
            self.mutate(stage, data)
        return StageResult(data=data, raw=json.dumps(data), model="mock-model", usage=None)

class WorkflowTests(unittest.TestCase):
    def execute(self, root, backend=None, articles=None, **kwargs):
        return run_workflow(query=QUERY, articles=articles if articles is not None else sources(),
                            output_dir=Path(root)/"run", backend=backend or FakeBackend(), **kwargs)

    def test_exact_agent_order_and_saved_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            backend = FakeBackend()
            result = self.execute(root, backend)
            self.assertEqual(backend.calls, ["planner", "researcher", "analyst", "reviewer"])
            self.assertEqual(result["publication_status"], "review_passed")
            for file in ("user_query.json", "planner_output.json", "researcher_output.json",
                         "analyst_report.json", "reviewer_output.json", "output.json",
                         "output.md", "run_manifest.json"):
                self.assertTrue((Path(root)/"run"/file).is_file(), file)
            self.assertEqual(result["correction_attempts"], 0)
            self.assertIsNone(result["agent_executions"][0]["usage"])

    def test_all_255_sources_and_all_readable_bodies_are_accounted_for(self):
        with tempfile.TemporaryDirectory() as root:
            backend = FakeBackend()
            state = self.execute(root, backend, sources(255, unavailable=109))
            evidence = json.loads((Path(root)/"run"/"researcher_output.json").read_text())
            self.assertEqual(state["source_count"], 255)
            self.assertEqual(state["readable_sources"], 146)
            self.assertEqual(len(evidence["article_assessments"]), 255)
            self.assertEqual(len(evidence["findings"]), 146)
            self.assertEqual(backend.calls.count("researcher"), 30)
            self.assertEqual(len({f["finding_id"] for f in evidence["findings"]}), 146)
            self.assertEqual(evidence["company_coverage"][1]["finding_ids"], [])

    def test_unavailable_sources_never_reach_research_model(self):
        with tempfile.TemporaryDirectory() as root:
            self.execute(root, articles=sources(2, unavailable=1))
            saved = json.loads((Path(root)/"run"/"stage_0002_researcher_input.json").read_text())
            self.assertEqual([a["article_id"] for a in saved["articles"]], ["a1"])

    def test_all_unavailable_sources_produce_honest_gap_report(self):
        with tempfile.TemporaryDirectory() as root:
            backend = FakeBackend()
            result = self.execute(root, backend, sources(2, unavailable=2))
            self.assertEqual(backend.calls, ["planner", "analyst", "reviewer"])
            report = json.loads((Path(root)/"run"/"analyst_report.json").read_text())
            self.assertEqual(report["insights"], [])
            self.assertEqual(result["readable_sources"], 0)

    def test_corrupt_sources_stop_before_any_call(self):
        with tempfile.TemporaryDirectory() as root:
            items = sources()
            items[0]["paragraphs"][0]["text"] = "Tampered"
            backend = FakeBackend()
            with self.assertRaisesRegex(ValueError, "hash"):
                self.execute(root, backend, items)
            self.assertEqual(backend.calls, [])

    def test_duplicate_sources_and_paragraphs_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_sources(sources() * 2)
        data = sources()
        data[0]["paragraphs"] *= 2
        text = "\n\n".join(p["text"] for p in data[0]["paragraphs"])
        data[0]["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "Duplicate paragraph"):
            validate_sources(data)

    def test_live_calls_require_explicit_flag(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "explicit"):
                run_workflow(query=QUERY, articles=sources(), output_dir=Path(root)/"run")

    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            self.execute(root)
            backend = FakeBackend()
            with self.assertRaises(FileExistsError):
                self.execute(root, backend)
            self.assertEqual(backend.calls, [])

    def test_planner_cannot_change_question_or_companies(self):
        for key, value in (("question", "Changed"), ("companies", ["Different company"]),
                           ("as_of_date", "2025-01-01"), ("period", "2020")):
            p = plan()
            p[key] = value
            with self.assertRaisesRegex(ValueError, "Planner changed"):
                validate_plan(ResearchPlan.model_validate(p), Query.model_validate(QUERY))

    def test_duplicate_planner_tasks_rejected(self):
        p = plan()
        p["tasks"] *= 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_plan(ResearchPlan.model_validate(p), Query.model_validate(QUERY))

    def test_arbitrary_company_and_feature_schema(self):
        p = plan()
        p["companies"] = ["A software vendor", "A logistics company"]
        q = {**QUERY, "companies": p["companies"]}
        validate_plan(ResearchPlan.model_validate(p), Query.model_validate(q))
        self.assertEqual(ResearchPlan.model_validate(p).tasks[0].dimension, "features")

    def test_invalid_research_citation_date_task_and_assessment_rejected(self):
        for mode in ("citation", "date", "task", "assessment"):
            def mutate(stage, data):
                if stage != "researcher":
                    return
                if mode == "citation":
                    data["findings"][0]["citations"][0]["paragraph_id"] = "unknown"
                elif mode == "date":
                    data["findings"][0]["publication_date"] = "2025-01-01"
                elif mode == "task":
                    data["findings"][0]["task_ids"] = ["unknown"]
                else:
                    data["article_assessments"] = []
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                backend = FakeBackend(mutate)
                with self.assertRaises(ValueError):
                    self.execute(root, backend)
                self.assertNotIn("analyst", backend.calls)
                self.assertTrue((Path(root)/"run"/"research_batch_0001.json").exists())

    def test_analyst_unknown_refs_or_missing_task_stop_before_review(self):
        for mode in ("citation", "task", "context", "question"):
            def mutate(stage, data):
                if stage != "analyst":
                    return
                if mode == "citation":
                    data["insights"][0]["evidence"]["finding_ids"] = ["unknown"]
                elif mode == "task":
                    data["answer_components"] = []
                elif mode == "context":
                    data["insights"][0]["context_keys"] = ["invented_budget"]
                else:
                    data["question"] = "Changed"
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                backend = FakeBackend(mutate)
                with self.assertRaises(ValueError):
                    self.execute(root, backend)
                self.assertNotIn("reviewer", backend.calls)

    def test_failed_review_preserves_report_and_hold(self):
        def mutate(stage, data):
            if stage == "reviewer":
                data["items"][0].update(disposition="needs_correction",
                    required_correction="Narrow the claim.")
        with tempfile.TemporaryDirectory() as root:
            result = self.execute(root, FakeBackend(mutate))
            self.assertEqual(result["publication_status"], "hold_for_human_review")
            output = (Path(root)/"run"/"output.md").read_text()
            self.assertIn("hold_for_human_review", output)
            self.assertIn("Narrow the claim.", output)

    def test_risk_issue_blocks_even_if_item_says_supported(self):
        def mutate(stage, data):
            if stage == "reviewer":
                data["items"][0]["risks"][0]["status"] = "issue"
                data["items"][0]["required_correction"] = "Correct the historical period."
        with tempfile.TemporaryDirectory() as root:
            result = self.execute(root, FakeBackend(mutate))
            self.assertEqual(result["overall_verdict"], "fail")

    def test_invented_review_excerpt_missing_item_risk_or_anchor_rejected(self):
        for mode in ("quote", "item", "risk", "anchor"):
            def mutate(stage, data):
                if stage != "reviewer":
                    return
                if mode == "quote":
                    data["items"][0]["anchors"][0]["excerpt"] = "Invented quotation never in the source."
                elif mode == "item":
                    data["items"].pop()
                elif mode == "risk":
                    data["items"][0]["risks"].pop()
                else:
                    data["items"][0]["anchors"] = []
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    self.execute(root, FakeBackend(mutate))
                folder = Path(root)/"run"
                self.assertFalse((folder/"output.md").exists())
                manifest = json.loads((folder/"run_manifest.json").read_text())
                self.assertEqual(manifest["publication_status"], "hold_for_human_review")

    def test_transport_failure_retains_inputs_and_failed_manifest(self):
        class Broken(FakeBackend):
            def generate(self, stage, schema, instructions, payload):
                if stage == "analyst":
                    raise RuntimeError("Simulated transport error")
                return super().generate(stage, schema, instructions, payload)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError, "transport"):
                self.execute(root, Broken())
            manifest = json.loads((Path(root)/"run"/"run_manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["agent_executions"][-1]["status"], "failed")
            self.assertTrue((Path(root)/"run"/"researcher_output.json").exists())

    def test_invalid_batch_size_and_blank_question_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                self.execute(root, batch_size=0)
        with self.assertRaises(ValueError):
            Query.model_validate({**QUERY, "question": " "})


    def test_other_industry_companies_work_end_to_end(self):
        from unittest.mock import patch
        request = {"question": "Compare Northstar Cloud and Harbor Analytics features.",
                   "companies": ["Northstar Cloud", "Harbor Analytics"]}
        with patch.dict(QUERY, request), tempfile.TemporaryDirectory() as root:
            state = self.execute(root)
            report = json.loads((Path(root)/"run"/"analyst_report.json").read_text())
            self.assertEqual(report["companies"], request["companies"])
            self.assertEqual(state["publication_status"], "review_passed")
            evidence = json.loads((Path(root)/"run"/"researcher_output.json").read_text())
            self.assertEqual(evidence["findings"][0]["dimension"], "features")
            self.assertEqual(evidence["findings"][0]["companies"], ["Northstar Cloud"])

    def test_malformed_model_json_preserves_raw_output_and_stops(self):
        class Malformed(FakeBackend):
            def generate(self, stage, schema, instructions, payload):
                if stage == "planner":
                    return StageResult(None, "not valid JSON", "mock", None)
                return super().generate(stage, schema, instructions, payload)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                self.execute(root, Malformed())
            directory = Path(root)/"run"
            self.assertEqual((directory/"stage_0001_planner_raw.txt").read_text(), "not valid JSON")
            self.assertEqual(json.loads((directory/"run_manifest.json").read_text())["status"], "failed")

    def test_live_cli_requires_explicit_permission_before_reading_inputs(self):
        import subprocess
        import sys
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8",
            "scripts/run_intelligence.py", "--question", "Compare fixture companies",
            "--articles", "does-not-exist.json", "--output-dir", "unused-test-dir"],
            capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Add --live", completed.stderr)

    def test_native_crewai_backend_uses_no_tools_delegation_or_retries(self):
        import types
        from unittest.mock import MagicMock, patch
        from intelligence.runtime import CrewAIBackend
        fake = types.ModuleType("crewai")
        for name in ("Agent", "Crew", "LLM", "Task"):
            setattr(fake, name, MagicMock(name=name))
        fake.Process = types.SimpleNamespace(sequential="sequential")
        parsed = ResearchPlan.model_validate(plan())
        output = types.SimpleNamespace(pydantic=parsed, raw=parsed.model_dump_json(),
                                       token_usage=None)
        fake.Crew.return_value.kickoff.return_value = output
        with patch.dict("sys.modules", {"crewai": fake}), \
             patch("analyst.runtime.prepare_crewai_runtime"), \
             patch("researcher.runtime.configure"), \
             patch("corpus.budget.check_context") as guard:
            result = CrewAIBackend({"planner": "test-model"}).generate(
                "planner", ResearchPlan, "Plan the task.", {"query": QUERY})
        self.assertEqual(result.model, "test-model")
        self.assertIsNone(result.usage)
        self.assertEqual(fake.Agent.call_args.kwargs["tools"], [])
        self.assertFalse(fake.Agent.call_args.kwargs["allow_delegation"])
        self.assertEqual(fake.LLM.call_args.kwargs["max_retries"], 0)
        self.assertEqual(fake.Task.call_args.kwargs["guardrail_max_retries"], 0)
        self.assertFalse(fake.Crew.call_args.kwargs["planning"])
        self.assertFalse(fake.Crew.call_args.kwargs["memory"])
        guard.assert_called_once()

if __name__ == "__main__":
    unittest.main()
