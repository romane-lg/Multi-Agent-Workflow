"""Manual independent scoring attached to exact saved reports; no automatic judges."""
import json
import uuid
from pathlib import Path
from benchmarking.benchmark import asset_path, file_hash
from benchmarking.schema import IndependentEvaluation, BenchmarkTask
from benchmarking.rubric import quality_score, WEIGHTS
from benchmarking.metrics import annotation_metrics
from benchmarking.logging import utc_now
from intelligence.workflow import save_json

def evaluation_template(run_dir, stage="final"):
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "experiment_run.json").read_text(encoding="utf-8"))
    if stage not in run["report_artifacts"]:
        raise ValueError("Requested report stage does not exist")
    return {"evaluation_id": uuid.uuid4().hex, "run_id": run["run_id"], "task_id": run["task_id"],
        "architecture_version": run["architecture_version"], "report_stage": stage,
        "report_sha256": run["report_artifacts"][stage]["sha256"],
        "benchmark_sha256": run["benchmark_sha256"], "evaluator_id": "",
        "evaluator_type": "human", "independent_of_internal_reviewer": True,
        "evaluated_at": utc_now(), "scores": {k: None for k in WEIGHTS},
        "criterion_comments": {k: "" for k in WEIGHTS}, "comments": "",
        "claim_inventory_complete": False, "error_inventory_complete": False,
        "component_inventory_complete": False, "claims": [], "components": [],
        "verified_errors": [], "reviewer_flags": [], "recovery_cases": [],
        "pre_recovery_errors": None, "post_recovery_errors": None, "review_time_seconds": None}

def validate_saved_evaluation(run_dir, value):
    run_dir = Path(run_dir)
    evaluation = IndependentEvaluation.model_validate(value)
    run = json.loads((run_dir / "experiment_run.json").read_text(encoding="utf-8"))
    if (evaluation.run_id != run["run_id"] or evaluation.task_id != run["task_id"]
        or evaluation.architecture_version != run["architecture_version"]
        or evaluation.benchmark_sha256 != run["benchmark_sha256"]):
        raise ValueError("Evaluation identity differs from the saved experiment")
    if run.get("human_reviewer_id") == evaluation.evaluator_id:
        raise ValueError("Independent evaluator must differ from the system human reviewer")
    artifact = run["report_artifacts"].get(evaluation.report_stage)
    if artifact is None or evaluation.report_sha256 != artifact["sha256"]:
        raise ValueError("Evaluation report does not match the saved artifact")
    if file_hash(asset_path(run_dir, artifact["path"])) != evaluation.report_sha256:
        raise ValueError("Saved report has changed since execution")
    if file_hash(run_dir / "benchmark_task.json") != run["task_snapshot_sha256"]:
        raise ValueError("Per-run benchmark task snapshot has changed")
    task = BenchmarkTask.model_validate_json((run_dir / "benchmark_task.json").read_text(encoding="utf-8"))
    metrics = annotation_metrics(evaluation, task)
    return evaluation, metrics

def save_evaluation(run_dir, value):
    run_dir = Path(run_dir)
    evaluation, metrics = validate_saved_evaluation(run_dir, value)
    result = {"evaluation": evaluation.model_dump(mode="json"),
              "quality_score": quality_score(evaluation.scores), "metrics": metrics,
              "rubric_version": "independent-human-v1"}
    folder = run_dir / "evaluations"
    folder.mkdir(exist_ok=True)
    save_json(folder / (evaluation.evaluation_id + ".json"), result)
    return result
