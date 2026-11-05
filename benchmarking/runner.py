"""Frozen-task runner for Version 1 only; no live calls without explicit opt-in."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from benchmarking.benchmark import load_benchmark, asset_path, file_hash
from benchmarking.schema import ExperimentConfig, Pricing
from benchmarking.logging import ObservedBackend, aggregate, utc_now
from intelligence.workflow import run_workflow, save_json

def commit_hash():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None

def environment_fingerprint():
    from importlib.metadata import version, PackageNotFoundError
    import platform
    versions = {}
    for name in ("crewai", "pydantic", "openai", "mlflow", "tiktoken"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    # Includes uncommitted source changes without recording secrets or environment.
    repo = Path(__file__).resolve().parents[1]
    paths = [p for folder in ("intelligence", "planner", "researcher", "analyst", "reviewer", "benchmarking")
             for p in (repo / folder).glob("*.py")]
    digest = hashlib.sha256()
    for p in sorted(paths):
        digest.update(p.relative_to(repo).as_posix().encode())
        digest.update(p.read_bytes())
    return {"python": platform.python_version(), "packages": versions,
            "workflow_source_sha256": digest.hexdigest()}

def run_experiments(*, benchmark_path, config, output_dir, live=False,
                    backend_factory=None, pricing=None):
    benchmark_path = Path(benchmark_path)
    benchmark = load_benchmark(benchmark_path, require_frozen=True)
    config = ExperimentConfig.model_validate(config)
    if benchmark.version != config.benchmark_version:
        raise ValueError("Experiment benchmark version differs from the frozen release")
    pricing = Pricing.model_validate(pricing) if pricing is not None else None
    selected_ids = config.task_ids or [t.task_id for t in benchmark.tasks]
    tasks = {t.task_id: t for t in benchmark.tasks}
    if not set(selected_ids) <= tasks.keys():
        raise ValueError("Unknown selected benchmark task")
    if backend_factory is None and not live:
        raise ValueError("Paid experiments require --live / live=True")
    # References and expected answers stay out of all model inputs.
    inputs = {tid: json.loads(asset_path(benchmark_path.parent, tasks[tid].input_snapshot)
                              .read_text(encoding="utf-8")) for tid in selected_ids}
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    save_json(root / "experiment_config.json", config)
    save_json(root / "benchmark_snapshot.json", benchmark)
    if pricing:
        save_json(root / "pricing_snapshot.json", pricing)
    experiment_id = uuid.uuid4().hex
    save_json(root / "experiment.json", {"experiment_id": experiment_id,
        "created_at": utc_now(), "execution_mode": "injected_backend" if backend_factory else "live",
        "source_benchmark": str(benchmark_path.resolve()),
        "benchmark_sha256": benchmark.sha256, "runtime": environment_fingerprint(),
        "code_commit": commit_hash()})
    run_ids = []
    for task_id in selected_ids:
        task = tasks[task_id]
        for repetition in range(1, config.repetitions + 1):
            run_id = uuid.uuid4().hex
            run_ids.append(run_id)
            run_dir = root / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=False)
            save_json(run_dir / "benchmark_task.json", task)
            observer = None
            started = time.monotonic()
            run = {"run_id": run_id, "experiment_id": experiment_id, "task_id": task_id,
                "repetition": repetition, "benchmark_version": benchmark.version,
                "benchmark_sha256": benchmark.sha256, "architecture_version": config.architecture_version,
                "timestamp": utc_now(), "code_commit": commit_hash(), "status": "running",
                "publication_status": "pending_review", "error_type": None,
                "model_configuration": config.models, "temperature": config.temperature,
                "seed": config.seed, "tool_configuration": config.tools,
                "retries": 0, "recovery_triggered": False, "report_artifacts": {},
                "currency": pricing.currency if pricing else None,
                "pricing_version": pricing.pricing_version if pricing else None,
                "pricing_effective_date": str(pricing.effective_date) if pricing and pricing.effective_date else None,
                "input_sha256": task.input_sha256,
                "task_snapshot_sha256": file_hash(run_dir / "benchmark_task.json")}
            try:
                backend = backend_factory() if backend_factory else None
                if backend is None:
                    from intelligence.runtime import CrewAIBackend
                    backend = CrewAIBackend(models=config.models)
                observer = ObservedBackend(backend, pricing)
                result = run_workflow(query={"question": task.question, "companies": task.companies,
                    "as_of_date": str(task.as_of_date), "period": task.period},
                    articles=inputs[task_id], output_dir=run_dir / "workflow",
                    backend=observer, batch_size=config.batch_size)
                run.update(status=result["status"], publication_status=result["publication_status"])
            except Exception as exc:
                run.update(status="failed", publication_status="hold_for_human_review",
                           error_type=type(exc).__name__)
            finally:
                # Keep initial/final bindings available even after a later-stage failure.
                for stage, relative in (("initial", "workflow/analyst_report.json"),
                                        ("final", "workflow/output.json")):
                    path = run_dir / relative
                    if path.exists():
                        run["report_artifacts"][stage] = {"path": relative, "sha256": file_hash(path)}
                rows = observer.rows if observer is not None else []
                run.update(aggregate(rows), end_time=utc_now(),
                           duration_seconds=round(time.monotonic() - started, 6),
                           workflow_completed=run["status"] == "completed")
                save_json(run_dir / "agent_metrics.json", rows)
                save_json(run_dir / "experiment_run.json", run)
    save_json(root / "experiment_summary.json", {"experiment_id": experiment_id, "run_ids": run_ids})
    return run_ids

def export_blind_packet(run_dir, output_dir):
    """Export pre-review evidence and Analyst draft only; no Reviewer or final output."""
    run_dir, output_dir = Path(run_dir), Path(output_dir)
    run = json.loads((run_dir / "experiment_run.json").read_text(encoding="utf-8"))
    names = ("user_query.json", "planner_output.json", "researcher_output.json", "analyst_report.json")
    for name in names:
        if not (run_dir / "workflow" / name).is_file():
            raise ValueError("Incomplete initial report cannot be exported")
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in names:
        shutil.copyfile(run_dir / "workflow" / name, output_dir / name)
    save_json(output_dir / "packet_manifest.json", {
        "run_id": run["run_id"], "task_id": run["task_id"], "report_stage": "initial",
        "files": {name: file_hash(output_dir / name) for name in names}})
