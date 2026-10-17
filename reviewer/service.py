"""Run one independent review and preserve its exact inputs and raw output."""
import hashlib
import json
from pathlib import Path
import time

from reviewer.crew import build_reviewer_crew, REVIEWER_INSTRUCTIONS
from reviewer.handoff import digest
from reviewer.render import render_review
from reviewer.schema import build_review_response_model, normalize_assessment
from reviewer.validation import finalize_review


def save_json(path: Path, value: dict):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def perform_review(review_input: dict, context: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    save_json(output_dir / "review_input.json", review_input)
    (output_dir / "review_input.txt").write_text(context, encoding="utf-8")
    started = time.monotonic()
    crew = build_reviewer_crew(review_input)
    output = crew.kickoff(inputs={"review_context": context})
    (output_dir / "reviewer_raw.txt").write_text(output.raw, encoding="utf-8")
    generated = output.pydantic.model_dump() if output.pydantic else json.loads(output.raw)
    if "revision_feedback" in review_input:
        # Validate every resolution slot before accepting the recheck.
        generated = build_review_response_model(review_input).model_validate(generated).model_dump()
        if any(not value["explanation"].strip() for value in generated["feedback_resolution"].values()):
            raise ValueError("Every feedback resolution requires an explanation")
    assessment = normalize_assessment(generated, review_input)
    run = {
        "reviewer_model": crew.agents[0].llm.model,
        "latency_seconds": round(time.monotonic() - started, 3),
        "usage": output.token_usage.model_dump() if output.token_usage else {},
        "prompt_sha256": hashlib.sha256(REVIEWER_INSTRUCTIONS.encode()).hexdigest(),
        "prompt_sha256_scope": "base Reviewer instructions",
        "task_description_sha256": hashlib.sha256(crew.tasks[0].description.encode()).hexdigest(),
        "output_schema_sha256": digest(build_review_response_model(review_input).model_json_schema()),
        "correction_loop_enabled": False, "correction_attempts": 0,
        "benchmark_evaluation_run": False,
    }
    if "revision_feedback" in review_input:
        run.update(correction_loop_enabled=True, correction_attempts=1,
                   feedback_resolution=generated["feedback_resolution"])
        save_json(output_dir / "feedback_resolution.json", generated["feedback_resolution"])
        lines = ["# Reviewer check of revision feedback", ""]
        for issue_id, decision in generated["feedback_resolution"].items():
            lines.extend([f"## {issue_id}: {decision['status']}", "", decision["explanation"], ""])
        (output_dir / "feedback_resolution.md").write_text("\n".join(lines), encoding="utf-8")
    result = finalize_review(assessment, review_input, run)
    save_json(output_dir / "review_report.json", result.model_dump())
    (output_dir / "review_report.md").write_text(render_review(result, review_input), encoding="utf-8")
    print("Reviewer verdict:", result.overall_verdict, "—", result.publication_status, flush=True)
    print("Review report:", output_dir / "review_report.md", flush=True)
    return result.model_dump()
