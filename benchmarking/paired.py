"""Shared initial generation and controlled branches with an identical presentation policy."""
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid
from analyst.schema import CompanyBrief
from intelligence.schema import Query, ResearchPlan, EvidencePack
from intelligence.workflow import run_workflow, save_json
from analyst.general import INSTRUCTIONS as ANALYST_PROMPT
from reviewer.general import INSTRUCTIONS as REVIEW_PROMPT, validate_review
from researcher.general import validate_sources, validate_batch
from benchmarking.benchmark import load_benchmark, file_hash, asset_path
from benchmarking.logging import ObservedBackend, aggregate, utc_now
from benchmarking.runner import commit_hash, environment_fingerprint
from benchmarking.experimental_schema import PairedConfig, VERSIONS, FizzeraReport, ExperimentalReview
from benchmarking.recovery import FIZZERA_RULES, REVIEW_ROUTING, targeted_issues, correct_once
from benchmarking.presentation import validate_fizzera, present

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def make_backend(config, live, factory):
    if factory is not None:
        return factory()
    if not live:
        raise ValueError("Paid stages require explicit --live / live=True")
    from intelligence.runtime import CrewAIBackend
    return CrewAIBackend({**config.models, **config.presentation_models})

def load_brief(path):
    brief = CompanyBrief.model_validate(read(path))
    text = "\n\f\n".join(p.text for p in brief.pages)
    if hashlib.sha256(text.encode()).hexdigest() != brief.text_sha256:
        raise ValueError("Company brief text hash mismatch")
    if len({p.page_number for p in brief.pages}) != len(brief.pages):
        raise ValueError("Duplicate company brief pages")
    return brief

def prepare_pair(*, benchmark_path, task_id, config, config_root, output_dir,
                 live=False, backend_factory=None, pricing=None, repetition=1):
    from benchmarking.schema import Pricing
    pricing = Pricing.model_validate(pricing) if pricing else None
    benchmark_path, config_root = Path(benchmark_path), Path(config_root)
    benchmark = load_benchmark(benchmark_path, require_frozen=True)
    config = PairedConfig.model_validate(config)
    if benchmark.version != config.benchmark_version:
        raise ValueError("Paired config benchmark version mismatch")
    tasks = {t.task_id: t for t in benchmark.tasks}
    if task_id not in tasks:
        raise ValueError("Unknown benchmark task")
    task = tasks[task_id]
    brief_path = asset_path(config_root, config.brief.path)
    if file_hash(brief_path) != config.brief.sha256:
        raise ValueError("Configured brief snapshot changed")
    brief = load_brief(brief_path)
    if brief.investment_envelope_cad is None or brief.product_launch_budget_cad is None:
        raise ValueError("Fizzera budget ceilings require manual checking")
    articles = read(asset_path(benchmark_path.parent, task.input_snapshot))
    validate_sources(articles)
    supplement = []
    if task_id in config.supplemental_evidence:
        binding = config.supplemental_evidence[task_id]
        path = asset_path(config_root, binding.path)
        if file_hash(path) != binding.sha256:
            raise ValueError("Supplemental evidence snapshot changed")
        supplement = [a.model_dump() for a in validate_sources(read(path))]
        original = {a["article_id"]: a for a in articles}
        if any(a["article_id"] in original and a != original[a["article_id"]] for a in supplement):
            raise ValueError("Supplement cannot mutate original sources")
    backend = make_backend(config, live, backend_factory)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    for name, value in (("benchmark_snapshot.json", benchmark), ("benchmark_task.json", task),
            ("experiment_config.json", config), ("company_brief.json", brief),
            ("supplemental_sources.json", supplement)):
        save_json(root / name, value)
    if pricing:
        save_json(root / "pricing_snapshot.json", pricing)
    observer = ObservedBackend(backend, pricing)
    query = {"question": task.question, "companies": task.companies,
        "as_of_date": str(task.as_of_date), "period": task.period,
        "company_context": {f"BRIEF p{p.page_number}": p.text for p in brief.pages}}
    start = time.monotonic()
    manifest = {"pair_id": uuid.uuid4().hex, "task_id": task_id, "repetition": repetition,
        "benchmark_version": benchmark.version, "benchmark_sha256": benchmark.sha256,
        "created_at": utc_now(), "code_commit": commit_hash(), "runtime": environment_fingerprint(),
        "status": "failed", "error_type": None, "hashes": {}}
    try:
        run_workflow(query=query, articles=articles, output_dir=root / "shared",
            backend=observer, batch_size=config.batch_size, report_schema=FizzeraReport,
            review_schema=ExperimentalReview, analyst_instructions=ANALYST_PROMPT + FIZZERA_RULES,
            reviewer_instructions=REVIEW_PROMPT + REVIEW_ROUTING,
            analysis_validator=lambda r,q: validate_fizzera(r,q,brief))
        manifest["status"] = "prepared"
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        raise
    finally:
        save_json(root / "shared_agent_metrics.json", observer.rows)
        manifest.update(shared_metrics=aggregate(observer.rows), duration_seconds=round(time.monotonic()-start,6))
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "pair_manifest.json":
                manifest["hashes"][path.relative_to(root).as_posix()] = file_hash(path)
        save_json(root / "pair_manifest.json", manifest)
    return manifest

def load_pair(root):
    root = Path(root)
    manifest = read(root / "pair_manifest.json")
    if manifest["status"] != "prepared":
        raise ValueError("Pair preparation did not complete")
    for relative, checksum in manifest["hashes"].items():
        if file_hash(asset_path(root, relative)) != checksum:
            raise ValueError("Shared input changed; paired reuse is forbidden")
    config = PairedConfig.model_validate(read(root / "experiment_config.json"))
    query = Query.model_validate(read(root / "shared/user_query.json"))
    plan = ResearchPlan.model_validate(read(root / "shared/planner_output.json"))
    evidence = EvidencePack.model_validate(read(root / "shared/researcher_output.json"))
    report = FizzeraReport.model_validate(read(root / "shared/analyst_report.json"))
    review = ExperimentalReview.model_validate(read(root / "shared/reviewer_output.json"))
    validate_batch(evidence, validate_sources([s.model_dump() for s in evidence.sources]), plan)
    from analyst.general import validate_report
    from planner.agent import validate_plan
    validate_plan(plan, query)
    validate_report(report, query, plan, evidence)
    brief = load_brief(root / "company_brief.json")
    validate_fizzera(report, query, brief)
    validate_review(review, report, evidence)
    return manifest, config, query, plan, evidence, report, review, brief

def run_variant(*, pair_dir, version, live=False, backend_factory=None,
                human_submission=None, packet_dir=None):
    from benchmarking.schema import Pricing
    pair_dir = Path(pair_dir)
    if version not in VERSIONS:
        raise ValueError("Unknown architecture version")
    manifest, config, query, plan, evidence, report, review, brief = load_pair(pair_dir)
    if version == "human_reviewer_v3" and human_submission is None:
        raise ValueError("V3 requires an independently submitted human review")
    backend = make_backend(config, live, backend_factory)
    pricing = Pricing.model_validate(read(pair_dir/"pricing_snapshot.json")) if (pair_dir/"pricing_snapshot.json").exists() else None
    observer = ObservedBackend(backend, pricing)
    run_id = uuid.uuid4().hex
    folder = pair_dir/"runs"/run_id
    folder.mkdir(parents=True, exist_ok=False)
    workflow = folder/"workflow"
    workflow.mkdir()
    shutil.copyfile(pair_dir/"benchmark_task.json", folder/"benchmark_task.json")
    for name in ("user_query.json", "planner_output.json", "researcher_output.json", "analyst_report.json"):
        shutil.copyfile(pair_dir/"shared"/name, workflow/name)
    save = lambda name,obj: save_json(workflow/name,obj)
    counter = 0
    def call(stage, schema, instructions, payload):
        nonlocal counter
        counter += 1
        save(f"stage_{counter:04d}_{stage}_input.json", payload)
        result = observer.generate(stage, schema, instructions, payload)
        (workflow/f"stage_{counter:04d}_{stage}_raw.txt").write_text(result.raw,encoding="utf-8")
        return schema.model_validate(result.data) if result.data is not None else schema.model_validate_json(result.raw)
    start = time.monotonic()
    shared_rows = read(pair_dir/"shared_agent_metrics.json")
    if version == "human_reviewer_v3":
        shared_rows = [r for r in shared_rows if r["agent_name"] != "reviewer"]
    run = {"run_id": run_id, "experiment_id": manifest["pair_id"], "pair_id": manifest["pair_id"],
        "task_id": manifest["task_id"], "repetition": manifest["repetition"],
        "benchmark_version": manifest["benchmark_version"], "benchmark_sha256": manifest["benchmark_sha256"],
        "architecture_version": version, "code_commit": manifest["code_commit"], "timestamp": utc_now(),
        "status": "failed", "publication_status": "hold_for_human_review", "error_type": None,
        "model_configuration": {**config.models, **config.presentation_models},
        "temperature": 0, "seed": None, "tool_configuration": "disabled", "retries": 0,
        "recovery_triggered": False, "recovery_attempts": 0, "reviewer_verdict": None,
        "report_artifacts": {}, "task_snapshot_sha256": file_hash(folder/"benchmark_task.json"),
        "input_sha256": file_hash(pair_dir/"shared/sources.json"),
        "shared_analyst_sha256": file_hash(pair_dir/"shared/analyst_report.json"),
        "shared_evidence_sha256": file_hash(pair_dir/"shared/researcher_output.json"),
        "shared_review_sha256": file_hash(pair_dir/"shared/reviewer_output.json") if version != "human_reviewer_v3" else None,
        "human_review_seconds": None, "human_labor_cost": None, "human_labor_currency": None,
        "currency": pricing.currency if pricing else None, "pricing_version": pricing.pricing_version if pricing else None,
        "pricing_effective_date": str(pricing.effective_date) if pricing and pricing.effective_date else None}
    try:
        if version == "human_reviewer_v3":
            from benchmarking.human import accept_submission
            submitted, review, verdict = accept_submission(pair_dir,packet_dir,human_submission)
            save("human_review.json",submitted)
            run.update(human_reviewer_id=submitted.reviewer_id,
                       human_review_seconds=(submitted.ended_at-submitted.started_at).total_seconds(),
                       human_labor_currency=submitted.labor_currency)
            if submitted.hourly_rate is not None:
                run["human_labor_cost"] = run["human_review_seconds"]/3600*submitted.hourly_rate
        else:
            save("initial_review.json",review)
            verdict = validate_review(review,report,evidence)
        if version == "targeted_recovery_v2" and verdict["overall_verdict"] == "fail":
            if targeted_issues(review,report):
                run.update(recovery_triggered=True,recovery_attempts=1,retries=1)
                save("pre_recovery_report.json",report)
                raw = read(pair_dir/"supplemental_sources.json")
                report,evidence,review,verdict = correct_once(query=query,plan=plan,evidence=evidence,
                    report=report,review=review,supplemental=validate_sources(raw) if raw else [],
                    call=call,save=save,validate_fizzera=lambda r,q:validate_fizzera(r,q,brief))
        save("selected_report.json",report)
        save("selected_evidence.json",evidence)
        save("selected_review.json",review)
        run["reviewer_verdict"] = verdict["overall_verdict"]
        presentation_dir = workflow/"executive"
        presentation_dir.mkdir()
        final = present(report=report,evidence=evidence,review=review,brief=brief,
            status=verdict["publication_status"],reviewer_type=VERSIONS[version]["reviewer_type"],
            call=call,save=lambda n,v:save_json(presentation_dir/n,v),folder=presentation_dir)
        run.update(status=final["status"],publication_status=final["publication_status"],
                   editorial_audit_passed=final.get("editorial_audit_passed",False))
    except Exception as exc:
        run.update(status="failed",error_type=type(exc).__name__,publication_status="hold_for_human_review")
    finally:
        mapping={"initial":"workflow/analyst_report.json","pre_recovery":"workflow/pre_recovery_report.json",
            "post_recovery":"workflow/post_recovery_report.json","final":"workflow/executive/executive_brief.json"}
        for stage,relative in mapping.items():
            if (folder/relative).exists():
                run["report_artifacts"][stage]={"path":relative,"sha256":file_hash(folder/relative)}
        if version=="targeted_recovery_v2" and "pre_recovery" not in run["report_artifacts"]:
            run["report_artifacts"]["pre_recovery"]=run["report_artifacts"]["initial"]
        rows=[{**r,"cost_allocation":"shared"} for r in shared_rows]+[
            {**r,"cost_allocation":"incremental"} for r in observer.rows]
        run.update(aggregate(rows),shared_metrics=aggregate(shared_rows),incremental_metrics=aggregate(observer.rows),
            end_time=utc_now(),duration_seconds=round(sum(r["duration_seconds"] for r in rows),6),
            incremental_wall_seconds=round(time.monotonic()-start,6),workflow_completed=run["status"]=="completed")
        run["review_time_seconds"]=run["human_review_seconds"] if version=="human_reviewer_v3" else sum(
            r["duration_seconds"] for r in rows if r["agent_name"]=="reviewer")
        save_json(folder/"agent_metrics.json",rows)
        save_json(folder/"experiment_run.json",run)
    return run
