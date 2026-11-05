"""Offline tests use synthetic evidence only; no public reference facts are claimed."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from benchmarking.benchmark import freeze_benchmark, load_benchmark, file_hash, canonical_hash
from benchmarking.schema import Benchmark, ExperimentConfig, IndependentEvaluation, Pricing
from benchmarking.rubric import quality_score, ANCHORS
from benchmarking.metrics import (unsupported_claim_rate, error_detection_precision,
    error_detection_recall, task_completeness, recovery_success_rate,
    error_reduction_rate, annotation_metrics)
from benchmarking.logging import normalized_usage, api_cost, aggregate, ObservedBackend
from benchmarking.runner import run_experiments, export_blind_packet
from benchmarking.evaluation import evaluation_template, save_evaluation
from benchmarking.export import export_results, SCHEMAS
from intelligence.test_workflow import QUERY, FakeBackend, sources
from intelligence.workflow import save_json

NOW = "2026-11-04T12:00:00Z"

def fixture_draft(root, count=1):
    root = Path(root)
    text = sources()[0]["paragraphs"][0]["text"]
    (root / "reference.txt").write_text(text, encoding="utf-8")
    save_json(root / "articles.json", sources())
    task = {"task_id": "T01", "category": "A", "question": QUERY["question"],
        "companies": QUERY["companies"], "as_of_date": QUERY["as_of_date"], "period": "2026",
        "expected_components": [{"component_id": "C1", "requirement": "Report fixture feature.",
                                 "reference_fact_ids": ["RF1"]}],
        "allowed_source_types": ["Synthetic fixtures only"],
        "reference_facts": [{"fact_id": "RF1", "text": text, "source_id": "S1", "excerpt": text}],
        "reference_sources": [{"source_id": "S1", "url": "https://example.com/fixture/0",
            "retrieved_at": NOW, "snapshot_path": "reference.txt", "sha256": file_hash(root / "reference.txt")}],
        "difficulty": "easy", "known_challenges": ["Synthetic testing only, not verified market evidence."],
        "verification_status": "verified",
        "verification": {"verified_by": "synthetic-test-verifier", "verified_at": NOW,
                         "notes": "Synthetic unit-test fixture; not a real benchmark release."},
        "input_snapshot": "articles.json", "input_sha256": file_hash(root / "articles.json")}
    tasks = []
    for i in range(count):
        t = copy.deepcopy(task)
        t["task_id"] = f"T{i+1:02d}"
        tasks.append(t)
    draft = {"schema_version": "ci-benchmark-v1", "version": "test-draft",
        "status": "draft", "created_at": NOW, "description": "Synthetic unit-test release.",
        "tasks": tasks, "sha256": None}
    save_json(root / "draft.json", draft)
    return root / "draft.json"

def fixture_release(root, count=1):
    return freeze_benchmark(fixture_draft(root, count), Path(root) / "releases", "test-v1")

class BenchmarkBackend(FakeBackend):
    def generate(self, stage, schema, instructions, payload):
        result = super().generate(stage, schema, instructions, payload)
        if stage == "planner":
            result.data["period"] = payload["query"]["period"]
            result.raw = json.dumps(result.data)
        result.usage = {"prompt_tokens": 10, "completion_tokens": 5,
                        "total_tokens": 15, "successful_requests": 1}
        result.model_calls = 1
        result.tool_calls = 0
        return result

def fixture_experiment(root, count=1, repetitions=1, factory=BenchmarkBackend):
    release = fixture_release(root, count)
    output = Path(root) / "experiment"
    ids = run_experiments(benchmark_path=release,
        config={"benchmark_version": "test-v1", "repetitions": repetitions},
        output_dir=output, backend_factory=factory)
    return output, ids

def human_evaluation(run_dir):
    value = evaluation_template(run_dir)
    value.update(evaluator_id="independent-human", scores={k: 3 for k in ANCHORS},
        criterion_comments={k: "Checked against synthetic reference." for k in ANCHORS},
        comments="Synthetic annotation fixture.", claim_inventory_complete=True,
        component_inventory_complete=True, error_inventory_complete=True,
        claims=[{"claim_id": "CL1", "location": "insights.i1.observed_fact",
            "text": "Synthetic erroneous claim", "accuracy": "incorrect", "support": "unsupported",
            "evidence_notes": "Independent synthetic annotation.", "reference_fact_ids": ["RF1"]}],
        components=[{"component_id": "C1", "verdict": "correct", "notes": "Fixture coverage checked."}],
        verified_errors=[{"error_id": "E1", "category": "incorrect_claim",
            "description": "Synthetic independently verified error.", "claim_id": "CL1",
            "component_id": None, "evidence_notes": "Compared with RF1."}],
        reviewer_flags=[{"flag_id": "F1", "reviewer_type": "ai", "description": "Synthetic true flag.",
            "matched_error_id": "E1", "verification_notes": "Human matched this flag."},
            {"flag_id": "F2", "reviewer_type": "ai", "description": "Synthetic false flag.",
             "matched_error_id": None, "verification_notes": "Human rejected this flag."}])
    return value

class BenchmarkTests(unittest.TestCase):
    def test_twelve_drafts_three_per_category_without_invented_facts(self):
        b = load_benchmark("benchmarks/ci_draft_v1.json")
        self.assertEqual(len(b.tasks), 12)
        for category in "ABCD":
            self.assertEqual(sum(t.category == category for t in b.tasks), 3)
        self.assertTrue(all(t.verification_status == "draft" for t in b.tasks))
        self.assertTrue(all(not t.reference_facts and not t.reference_sources for t in b.tasks))

    def test_draft_cannot_execute_or_freeze(self):
        with self.assertRaisesRegex(ValueError, "frozen"):
            load_benchmark("benchmarks/ci_draft_v1.json", require_frozen=True)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "verified"):
                freeze_benchmark("benchmarks/ci_draft_v1.json", root, "v1")

    def test_schema_rejects_missing_fields_duplicate_ids_and_fake_verification(self):
        b = load_benchmark("benchmarks/ci_draft_v1.json").model_dump(mode="json")
        for mutate in ("missing", "duplicate", "verified"):
            d = copy.deepcopy(b)
            if mutate == "missing":
                del d["tasks"][0]["question"]
            elif mutate == "duplicate":
                d["tasks"][1]["task_id"] = d["tasks"][0]["task_id"]
            else:
                d["tasks"][0]["verification_status"] = "verified"
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                Benchmark.model_validate(d)

    def test_freeze_creates_new_hashed_portable_release_and_preserves_draft(self):
        with tempfile.TemporaryDirectory() as root:
            draft = fixture_draft(root)
            original = draft.read_bytes()
            path = freeze_benchmark(draft, Path(root)/"releases", "test-v1")
            b = load_benchmark(path, require_frozen=True)
            self.assertEqual(b.sha256, canonical_hash(b))
            self.assertEqual(draft.read_bytes(), original)
            self.assertTrue((path.parent / b.tasks[0].input_snapshot).exists())
            with self.assertRaises(FileExistsError):
                freeze_benchmark(draft, Path(root)/"releases", "test-v1")
            with self.assertRaisesRegex(ValueError, "new version"):
                freeze_benchmark(draft, Path(root)/"releases", "test-draft")

    def test_frozen_content_and_input_tampering_rejected(self):
        for mode in ("question", "input", "reference"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                path = fixture_release(root)
                b = load_benchmark(path)
                if mode == "question":
                    d = json.loads(path.read_text())
                    d["tasks"][0]["question"] = "Changed question"
                    path.write_text(json.dumps(d))
                else:
                    relative = b.tasks[0].input_snapshot if mode == "input" else b.tasks[0].reference_sources[0].snapshot_path
                    (path.parent / relative).write_text("tampered", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "checksum|hash"):
                    load_benchmark(path, require_frozen=True)

    def test_invalid_reference_excerpt_and_escaping_snapshot_rejected(self):
        for mode in ("excerpt", "path"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                draft = fixture_draft(root)
                d = json.loads(draft.read_text())
                if mode == "excerpt":
                    d["tasks"][0]["reference_facts"][0]["excerpt"] = "Never in the snapshot"
                else:
                    d["tasks"][0]["input_snapshot"] = "../outside.json"
                draft.write_text(json.dumps(d))
                with self.assertRaises(ValueError):
                    freeze_benchmark(draft, Path(root)/"releases", "test-v1")

class ScoringTests(unittest.TestCase):
    def test_weighted_quality_scores_and_all_25_anchors(self):
        self.assertEqual(quality_score({k: 4 for k in ANCHORS}), 100)
        self.assertEqual(quality_score({k: 0 for k in ANCHORS}), 0)
        self.assertEqual(quality_score({k: 2 for k in ANCHORS}), 50)
        scores = {k: 0 for k in ANCHORS}
        scores["factual_accuracy"] = 4
        self.assertEqual(quality_score(scores), 30)
        self.assertEqual(sum(len(a) for a in ANCHORS.values()), 25)

    def test_invalid_scores_rejected(self):
        for invalid in (True, 5, -1, 2.5, "3"):
            scores = {k: 3 for k in ANCHORS}
            scores["factual_accuracy"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                quality_score(scores)
        with self.assertRaises(ValueError):
            quality_score({})

    def test_objective_metrics_and_zero_denominators(self):
        self.assertEqual(unsupported_claim_rate(1, 4), .25)
        self.assertEqual(error_detection_precision(2, 4), .5)
        self.assertEqual(error_detection_recall(2, 5), .4)
        self.assertEqual(task_completeness(3, 4), .75)
        self.assertEqual(recovery_success_rate(1, 2), .5)
        self.assertEqual(error_reduction_rate(4, 1), .75)
        self.assertEqual(error_reduction_rate(2, 3), -.5)
        for fn in (unsupported_claim_rate, error_detection_precision, error_detection_recall,
                   task_completeness, recovery_success_rate, error_reduction_rate):
            self.assertIsNone(fn(0, 0))

    def test_invalid_metric_counts_rejected(self):
        for fn in (unsupported_claim_rate, error_detection_precision, error_detection_recall,
                   task_completeness, recovery_success_rate):
            with self.assertRaises(ValueError):
                fn(2, 1)
            with self.assertRaises(ValueError):
                fn(-1, 3)

class UsageTests(unittest.TestCase):
    def test_unknown_usage_is_not_zero_and_known_values_aggregate(self):
        unknown = normalized_usage(None)
        self.assertIsNone(unknown["total_tokens"])
        known = normalized_usage({"input_tokens": 5, "output_tokens": 2, "successful_requests": 1})
        self.assertEqual(known["total_tokens"], 7)
        combined = aggregate([known, unknown])
        self.assertIsNone(combined["total_tokens"])
        self.assertEqual(combined["known_total_tokens"], 7)

    def test_cost_uses_configured_versioned_rates(self):
        pricing = Pricing.model_validate({"currency": "USD", "pricing_version": "synthetic-v1",
            "effective_date": "2026-01-01",
            "models": {"mock": {"input_per_million": 2, "output_per_million": 4}}})
        usage = normalized_usage({"prompt_tokens": 100, "completion_tokens": 50})
        self.assertEqual(api_cost("mock", usage, pricing), .0004)
        self.assertIsNone(api_cost("unknown", usage, pricing))
        self.assertIsNone(api_cost("mock", normalized_usage(None), pricing))
        with self.assertRaises(ValueError):
            Pricing.model_validate({"currency": "USD", "pricing_version": "bad",
                "effective_date": None, "models": {"m": {"input_per_million": 1, "output_per_million": 1}}})

    def test_cached_token_cost_requires_cache_rates_and_counts(self):
        pricing = Pricing.model_validate({"currency": "USD", "pricing_version": "cache-fixture",
            "effective_date": "2026-01-01", "models": {"m": {
                "input_per_million": 2, "output_per_million": 4, "cached_input_per_million": 1}}})
        usage = normalized_usage({"input_tokens": 100, "output_tokens": 50,
                                  "input_tokens_details": {"cached_tokens": 40}})
        self.assertEqual(api_cost("m", usage, pricing), .00036)
        self.assertIsNone(api_cost("m", normalized_usage({"input_tokens": 100, "output_tokens": 50}), pricing))

class RunnerTests(unittest.TestCase):
    def test_exact_existing_architecture_and_intermediate_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            manifest = json.loads((run_dir/"experiment_run.json").read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["total_tokens"], 60)
            self.assertEqual(manifest["model_calls"], 4)
            self.assertEqual(manifest["tool_calls"], 0)
            self.assertIsNone(manifest["api_cost"])
            stages = json.loads((run_dir/"agent_metrics.json").read_text())
            self.assertEqual([s["agent_name"] for s in stages], ["planner", "researcher", "analyst", "reviewer"])
            self.assertFalse(manifest["recovery_triggered"])
            self.assertEqual(manifest["retries"], 0)
            self.assertIn("initial", manifest["report_artifacts"])
            self.assertIn("final", manifest["report_artifacts"])
            planner_input = (run_dir/"workflow"/"stage_0001_planner_input.json").read_text()
            self.assertNotIn("reference_facts", planner_input)
            self.assertNotIn("RF1", planner_input)

    def test_subset_repetitions_and_unique_runs(self):
        with tempfile.TemporaryDirectory() as root:
            release = fixture_release(root, 2)
            ids = run_experiments(benchmark_path=release,
                config={"benchmark_version": "test-v1", "task_ids": ["T02"], "repetitions": 2},
                output_dir=Path(root)/"runs", backend_factory=BenchmarkBackend)
            self.assertEqual(len(set(ids)), 2)
            for rid in ids:
                row = json.loads((Path(root)/"runs"/"runs"/rid/"experiment_run.json").read_text())
                self.assertEqual(row["task_id"], "T02")

    def test_failures_logged_without_sensitive_exception_text(self):
        class Broken(BenchmarkBackend):
            def generate(self, stage, schema, instructions, payload):
                if stage == "analyst":
                    raise RuntimeError("Secret sk-do-not-log-this-value")
                return super().generate(stage, schema, instructions, payload)
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root, factory=Broken)
            directory = experiment/"runs"/ids[0]
            row = json.loads((directory/"experiment_run.json").read_text())
            metrics = (directory/"agent_metrics.json").read_text()
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["error_type"], "RuntimeError")
            self.assertNotIn("sk-do-not-log", metrics)
            self.assertIsNone(row["total_tokens"])

    def test_no_live_calls_without_flag_and_reject_drafts_versions_and_task_ids(self):
        with tempfile.TemporaryDirectory() as root:
            release = fixture_release(root)
            for config, pattern in (({"benchmark_version": "wrong"}, "version"),
                    ({"benchmark_version": "test-v1", "task_ids": ["unknown"]}, "Unknown"),
                    ({"benchmark_version": "test-v1"}, "live")):
                with self.subTest(config=config), self.assertRaisesRegex(ValueError, pattern):
                    run_experiments(benchmark_path=release, config=config, output_dir=Path(root)/"no-run")
            self.assertFalse((Path(root)/"no-run").exists())

    def test_configuration_rejects_future_architectures_and_unsupported_settings(self):
        for extra in ({"architecture_version": "targeted_recovery_v2"}, {"temperature": .5},
                      {"seed": 123}, {"repetitions": 0}, {"batch_size": 6}, {"task_ids": []},
                      {"models": {"analyst": "only-one-model"}}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                ExperimentConfig.model_validate({"benchmark_version": "v1", **extra})

    def test_blind_packet_excludes_ai_feedback_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            packet = Path(root)/"blind"
            export_blind_packet(run_dir, packet)
            self.assertEqual((packet/"analyst_report.json").read_bytes(),
                             (run_dir/"workflow"/"analyst_report.json").read_bytes())
            self.assertFalse(any("review" in p.name for p in packet.iterdir()))
            self.assertFalse((packet/"output.json").exists())
            with self.assertRaises(FileExistsError):
                export_blind_packet(run_dir, packet)

    def test_cli_rejects_unapproved_live_run_before_reading_files(self):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-m", "benchmarking", "run",
            "--benchmark", "missing", "--config", "missing", "--output-dir", "unused"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Add --live", result.stderr)

class AnnotationAndExportTests(unittest.TestCase):
    def test_manual_scores_annotations_and_all_six_csv_exports(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            saved = save_evaluation(run_dir, human_evaluation(run_dir))
            self.assertEqual(saved["quality_score"], 75)
            self.assertEqual(saved["metrics"]["unsupported_claim_rate"], 1)
            self.assertEqual(saved["metrics"]["error_detection_precision"], .5)
            self.assertEqual(saved["metrics"]["error_detection_recall"], 1)
            counts = export_results(experiment, Path(root)/"csv")
            self.assertEqual(counts["experiment_runs"], 1)
            self.assertEqual(counts["agent_metrics"], 4)
            self.assertEqual(counts["quality_scores"], 1)
            self.assertEqual(counts["claim_annotations"], 1)
            self.assertEqual(counts["error_detection"], 3)
            self.assertEqual(counts["benchmark_tasks"], 1)
            for name, fields in SCHEMAS.items():
                with (Path(root)/"csv"/(name+".csv")).open(encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    self.assertEqual(reader.fieldnames, list(fields))
                    rows = list(reader)
                    self.assertEqual(len(rows), counts[name])
            with (Path(root)/"csv"/"experiment_runs.csv").open(newline="") as handle:
                row = next(csv.DictReader(handle))
                self.assertEqual(row["api_cost"], "")
                self.assertEqual(row["run_id"], ids[0])
            with (Path(root)/"csv"/"quality_scores.csv").open(newline="") as handle:
                row = next(csv.DictReader(handle))
                self.assertEqual(float(row["task_completeness"]), 1)
                self.assertEqual(row["task_completeness_score"], "3")
            self.assertTrue((Path(root)/"csv"/"data_dictionary.json").exists())

    def test_empty_evaluation_tables_still_export_headers(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, _ = fixture_experiment(root)
            counts = export_results(experiment, Path(root)/"csv")
            self.assertEqual(counts["quality_scores"], 0)
            self.assertEqual(counts["claim_annotations"], 0)

    def test_reviewer_verdict_cannot_supply_independent_score(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            data = human_evaluation(run_dir)
            data["evaluator_type"] = "internal_ai_reviewer"
            with self.assertRaises(ValueError):
                save_evaluation(run_dir, data)
            data = human_evaluation(run_dir)
            data["independent_of_internal_reviewer"] = False
            with self.assertRaises(ValueError):
                save_evaluation(run_dir, data)

    def test_report_hash_and_task_hash_bind_evaluations(self):
        for mode in ("report", "task", "run"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                experiment, ids = fixture_experiment(root)
                run_dir = experiment/"runs"/ids[0]
                data = human_evaluation(run_dir)
                if mode == "report":
                    (run_dir/"workflow"/"output.json").write_text("{}")
                elif mode == "task":
                    (run_dir/"benchmark_task.json").write_text("{}")
                else:
                    data["run_id"] = "wrong-run"
                with self.assertRaises(ValueError):
                    save_evaluation(run_dir, data)

    def test_incomplete_annotations_leave_objective_metrics_undefined(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            data = human_evaluation(run_dir)
            for key in ("claim_inventory_complete", "error_inventory_complete", "component_inventory_complete"):
                data[key] = False
            result = save_evaluation(run_dir, data)
            for key in ("unsupported_claim_rate", "error_detection_precision",
                        "error_detection_recall", "task_completeness"):
                self.assertIsNone(result["metrics"][key])

    def test_duplicate_flags_do_not_inflate_recall(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            data = human_evaluation(run_dir)
            data["reviewer_flags"][1]["matched_error_id"] = "E1"
            result = save_evaluation(run_dir, data)
            self.assertEqual(result["metrics"]["error_detection_recall"], 1)

    def test_invalid_complete_components_unknown_errors_and_duplicate_ids_rejected(self):
        for mode in ("component", "error", "duplicate", "unaccounted"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                experiment, ids = fixture_experiment(root)
                run_dir = experiment/"runs"/ids[0]
                data = human_evaluation(run_dir)
                if mode == "component":
                    data["components"] = []
                elif mode == "error":
                    data["reviewer_flags"][0]["matched_error_id"] = "unverified"
                elif mode == "duplicate":
                    data["claims"] *= 2
                else:
                    data["verified_errors"] = []
                    data["reviewer_flags"] = []
                with self.assertRaises(ValueError):
                    save_evaluation(run_dir, data)

    def test_recovery_metric_schema_is_available_but_baseline_cannot_recover(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            data = human_evaluation(experiment/"runs"/ids[0])
            data.update(pre_recovery_errors=4, post_recovery_errors=2)
            with self.assertRaises(ValueError):
                IndependentEvaluation.model_validate(data)
            data["architecture_version"] = "targeted_recovery_v2"
            self.assertEqual(IndependentEvaluation.model_validate(data).post_recovery_errors, 2)

    def test_evaluation_results_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            run_dir = experiment/"runs"/ids[0]
            data = human_evaluation(run_dir)
            save_evaluation(run_dir, data)
            with self.assertRaises(FileExistsError):
                save_evaluation(run_dir, data)


class InstrumentationEdgeTests(unittest.TestCase):
    def test_backend_setup_failure_is_logged_and_remaining_repetitions_continue(self):
        def broken_factory():
            raise RuntimeError("Synthetic setup failure")
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root, repetitions=2, factory=broken_factory)
            self.assertEqual(len(ids), 2)
            for rid in ids:
                run = json.loads((experiment/"runs"/rid/"experiment_run.json").read_text())
                self.assertEqual(run["status"], "failed")
                self.assertEqual(run["error_type"], "RuntimeError")
                self.assertIsNone(run["total_tokens"])
                self.assertEqual(json.loads((experiment/"runs"/rid/"agent_metrics.json").read_text()), [])

    def test_pricing_problem_cannot_change_successful_agent_result(self):
        from intelligence.runtime import StageResult
        class Backend:
            def __init__(self):
                self.result = StageResult({}, "unchanged raw", "m",
                    {"input_tokens": 5, "output_tokens": 3, "cached_input_tokens": 20})
            def generate(self, *args):
                return self.result
        pricing = Pricing.model_validate({"currency": "USD", "pricing_version": "fixture",
            "effective_date": "2026-01-01", "models": {
                "m": {"input_per_million": 1, "output_per_million": 1}}})
        backend = Backend()
        observed = ObservedBackend(backend, pricing)
        result = observed.generate("planner", None, "original instructions", {"original": "payload"})
        self.assertIs(result, backend.result)
        self.assertIsNone(observed.rows[0]["api_cost"])
        self.assertEqual(observed.rows[0]["status"], "completed")
        self.assertEqual(observed.rows[0]["pricing_error_type"], "ValueError")

    def test_whole_frozen_benchmark_selection_executes_every_task(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root, count=2)
            tasks = {json.loads((experiment/"runs"/rid/"experiment_run.json").read_text())["task_id"]
                     for rid in ids}
            self.assertEqual(tasks, {"T01", "T02"})

    def test_csv_export_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as root:
            experiment, ids = fixture_experiment(root)
            export_results(experiment, Path(root)/"csv")
            with self.assertRaises(FileExistsError):
                export_results(experiment, Path(root)/"csv")

if __name__ == "__main__":
    unittest.main()
