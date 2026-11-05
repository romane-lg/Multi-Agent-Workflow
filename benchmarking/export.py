"""Six joinable UTF-8 CSV tables plus a machine-readable data dictionary."""
import csv
import json
from pathlib import Path

from benchmarking.schema import IndependentEvaluation
from benchmarking.rubric import quality_score
from benchmarking.metrics import annotation_metrics

COMMON = {"run_id": "Stable workflow execution identifier.",
          "task_id": "Frozen benchmark task identifier."}
EVAL = {**COMMON, "evaluation_id": "Independent human assessment identifier.",
        "evaluator_id": "Independent evaluator identifier.",
        "report_stage": "initial, final, pre_recovery or post_recovery.",
        "architecture_version": "Architecture under evaluation."}
SCHEMAS = {
"experiment_runs": {**COMMON,
    "experiment_id": "Group of selected task repetitions.", "repetition": "One-based repetition.",
    "benchmark_version": "Immutable benchmark release version.",
    "benchmark_sha256": "Canonical frozen benchmark checksum.", "architecture_version": "Only sequential_v1 executes in Phase 1.",
    "timestamp": "Execution start, UTC ISO timestamp.", "end_time": "Execution end, UTC ISO timestamp.",
    "duration_seconds": "Wall time for the workflow execution.", "status": "completed or failed.",
    "workflow_completed": "Whether the workflow completed structurally.",
    "publication_status": "Runtime review state, not independent quality.",
    "model_configuration": "JSON object of requested models by agent.", "temperature": "Configured temperature, currently zero.",
    "seed": "Unavailable; no seed is passed by the current backend.", "tool_configuration": "disabled.",
    "input_tokens": "Full-run tokens, blank if any execution has unknown usage.",
    "output_tokens": "Full-run generated tokens, blank if any unknown.",
    "total_tokens": "Full-run tokens; provider total or input plus output.",
    "model_calls": "Provider/framework reported successful requests; unknown stays blank.",
    "tool_calls": "Reported tool executions; disabled native tools yield zero.",
    "api_cost": "Configured token-rate estimate, blank when any execution cost is unknown.",
    "known_total_tokens": "Sum of available totals; partial and not a full-run total.",
    "known_api_cost": "Sum of available costs; partial and not a full-run total.",
    "currency": "ISO currency for configured pricing.", "pricing_version": "User-maintained price schedule identifier.",
    "pricing_effective_date": "Date for the configured pricing schedule.",
    "retries": "Intentional workflow retries, zero in baseline.", "recovery_triggered": "False in baseline.",
    "input_sha256": "Exact frozen workflow input checksum.", "code_commit": "Git HEAD when available.",
    "task_snapshot_sha256": "Checksum binding the per-run task reference snapshot.",
    "error_type": "Exception class only; raw exception text is not exported."},
"agent_metrics": {**COMMON,
    "execution_index": "One-based agent execution index; Researcher may execute in batches.",
    "agent_name": "planner, researcher, analyst or reviewer.",
    "start_time": "Agent execution start, UTC ISO.", "end_time": "Agent execution end, UTC ISO.",
    "duration_seconds": "Backend execution wall time.", "model": "Reported/configured model name.",
    "model_version": "Provider snapshot version when separately available; otherwise blank.",
    "status": "Backend completed or failed; later schema failure is recorded at workflow level.",
    "input_tokens": "Reported input/prompt tokens.", "output_tokens": "Reported output/completion tokens.",
    "total_tokens": "Reported total or mechanically summed known input/output.",
    "cached_input_tokens": "Reported cached input tokens, blank if unknown.",
    "model_calls": "Reported successful requests or explicit backend count.",
    "tool_calls": "Explicit backend tool count, blank if unavailable.",
    "api_cost": "Configured token-rate estimate, not an invoice.",
    "currency": "Pricing currency.", "pricing_version": "Price schedule version.",
    "pricing_effective_date": "Price schedule effective date.",
    "cost_method": "configured_token_rates_estimate or blank.",
    "pricing_error_type": "Accounting validation failure, if any; agent result remains unchanged.",
    "error_type": "Exception class.", "error_message": "Generic safe error summary."},
"quality_scores": {**EVAL, "report_sha256": "Hash of exactly assessed report artifact.",
    "benchmark_sha256": "Reference benchmark hash.",
    "evaluated_at": "Human assessment timestamp.", "rubric_version": "independent-human-v1.",
    "factual_accuracy": "Human criterion score 0-4.", "task_completeness_score": "Human rubric score 0-4.",
    "evidence_quality": "Human criterion score 0-4.", "claim_support": "Human criterion score 0-4.",
    "clarity_usefulness": "Human criterion score 0-4.", "quality_score": "Weighted human score 0-100.",
    "criterion_comments": "JSON comments per human rubric criterion.", "comments": "Overall human comments.",
    "unsupported_claim_rate": "Unsupported claims divided by all annotated factual claims.",
    "error_detection_precision": "Verified true-positive flags divided by all annotated flags.",
    "error_detection_recall": "Distinct detected verified errors divided by all verified errors.",
    "task_completeness": "Correct required components divided by all required components.",
    "recovery_success_rate": "Fully resolved target-error cases divided by all recovery cases; blank in baseline.",
    "error_reduction_rate": "(Before-after)/before; blank in baseline or zero denominator.",
    "claim_inventory_complete": "Human asserts all factual claims were enumerated.",
    "error_inventory_complete": "Human asserts errors and reviewer flags were exhaustively annotated.",
    "component_inventory_complete": "Human asserts all frozen required components were assessed.",
    "review_time_seconds": "Independent evaluator's measured time, when available."},
"claim_annotations": {**EVAL, "claim_id": "Stable factual-claim annotation ID.",
    "location": "Exact report item/paragraph location.", "text": "Unmodified annotated claim text.",
    "accuracy": "correct, incorrect or unverifiable.",
    "support": "supported, unsupported or unverifiable; independent of accuracy.",
    "evidence_notes": "Human verification rationale.", "reference_fact_ids": "JSON list of benchmark reference facts."},
"error_detection": {**EVAL,
    "row_type": "verified_error or reviewer_flag.",
    "error_id": "Independently verified error ID.", "flag_id": "Reviewer flag ID.",
    "reviewer_type": "ai or human, when a flag.",
    "category": "Independent error category.", "description": "Error or flag description.",
    "claim_id": "Linked factual claim, if applicable.", "component_id": "Linked missing/incorrect component.",
    "matched_error_id": "Verified error matched to a flag; blank means false positive.",
    "detection_status": "detected, missed, true_positive or false_positive.",
    "verification_notes": "Independent human rationale; never automatic AI ground truth."},
"benchmark_tasks": {
    "benchmark_version": "Frozen release version.", "benchmark_sha256": "Release checksum.",
    "task_id": "Stable benchmark question ID.", "category": "A company, B comparison, C developments, D challenges.",
    "question": "Exact user question.", "companies": "JSON company names.", "as_of_date": "Fixed cutoff date.",
    "period": "Fixed research window.", "expected_components": "JSON required answer components.",
    "allowed_source_types": "JSON permitted evidence types.", "reference_facts": "JSON human-verified reference facts.",
    "reference_sources": "JSON URLs, retrieval dates and snapshot hashes.",
    "difficulty": "easy, medium or hard.", "known_challenges": "JSON challenge conditions.",
    "verification_status": "draft or verified.", "verification": "JSON human verification attestation.",
    "input_snapshot": "Relative frozen input path.", "input_sha256": "Frozen article input checksum."}
}

def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value

def export_results(experiment_dir, output_dir):
    from benchmarking.evaluation import validate_saved_evaluation
    experiment_dir, output_dir = Path(experiment_dir), Path(output_dir)
    tables = {name: [] for name in SCHEMAS}
    benchmark = json.loads((experiment_dir / "benchmark_snapshot.json").read_text(encoding="utf-8"))
    for task in benchmark["tasks"]:
        tables["benchmark_tasks"].append({**task, "benchmark_version": benchmark["version"],
                                         "benchmark_sha256": benchmark["sha256"]})
    for folder in sorted((experiment_dir / "runs").iterdir()):
        if not folder.is_dir():
            continue
        run = json.loads((folder / "experiment_run.json").read_text(encoding="utf-8"))
        common = {"run_id": run["run_id"], "task_id": run["task_id"]}
        tables["experiment_runs"].append(run)
        rows = json.loads((folder / "agent_metrics.json").read_text(encoding="utf-8"))
        tables["agent_metrics"].extend({**common, **row} for row in rows)
        for path in sorted((folder / "evaluations").glob("*.json")):
            saved = json.loads(path.read_text(encoding="utf-8"))
            evaluation, metrics = validate_saved_evaluation(folder, saved["evaluation"])
            e = evaluation.model_dump(mode="json")
            context = {k: e[k] for k in EVAL}
            scores = {**e, **evaluation.scores, **metrics,
                      "task_completeness_score": evaluation.scores["task_completeness"],
                      "quality_score": quality_score(evaluation.scores),
                      "rubric_version": "independent-human-v1"}
            tables["quality_scores"].append(scores)
            tables["claim_annotations"].extend({**context, **c} for c in e["claims"])
            detected = {flag.matched_error_id for flag in evaluation.reviewer_flags}
            for error in e["verified_errors"]:
                tables["error_detection"].append({**context, **error, "row_type": "verified_error",
                    "detection_status": "detected" if error["error_id"] in detected else "missed",
                    "verification_notes": error["evidence_notes"]})
            for flag in e["reviewer_flags"]:
                tables["error_detection"].append({**context, **flag, "row_type": "reviewer_flag",
                    "detection_status": "true_positive" if flag["matched_error_id"] else "false_positive"})
    output_dir.mkdir(parents=True, exist_ok=False)
    for table, fields in SCHEMAS.items():
        with (output_dir / (table + ".csv")).open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
            writer.writeheader()
            for row in tables[table]:
                writer.writerow({key: csv_value(row.get(key)) for key in fields})
    with (output_dir / "data_dictionary.json").open("x", encoding="utf-8") as handle:
        json.dump({"encoding": "UTF-8", "missing_value": "",
                   "nested_values": "JSON strings", "tables": SCHEMAS}, handle, indent=2)
    return {table: len(rows) for table, rows in tables.items()}
