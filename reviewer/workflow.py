"""CrewAI orchestration for saved-run review and full Researcher/Analyst/Reviewer runs."""
import json
from pathlib import Path

import mlflow
from crewai.flow.flow import Flow, listen, start

from reviewer.handoff import make_review_input
from reviewer.schema import ReviewResult
from reviewer.service import perform_review


class SavedAnalysisReviewFlow(Flow):
    def __init__(self, *, analysis_run: Path, output_dir: Path):
        super().__init__(tracing=False)
        self.analysis_run = analysis_run
        self.output_dir = output_dir

    @start()
    def verify_review_handoff(self):
        return make_review_input(self.analysis_run)

    @listen(verify_review_handoff)
    def reviewer_stage(self, handoff):
        payload, context = handoff
        return perform_review(payload, context, self.output_dir)


def review_completed_analysis(output_dir: Path, analyst_result: dict):
    # The exact just-saved analysis and frozen handoff are the review inputs.
    payload, context = make_review_input(output_dir)
    if payload["analyst_report"] != analyst_result:
        raise ValueError("Saved Analyst output differs from its Flow result")
    result = perform_review(payload, context, output_dir / "review")
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(
        workflow="CrewAI Flow: Researcher -> validated handoff -> Analyst -> independent Reviewer",
        reviewer_run=True, reviewer_verdict=result["overall_verdict"],
        review_status="completed",
        publication_status=result["publication_status"], reviewer_run_details=result["run"],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return result


@mlflow.trace(name="independent_fizzera_review", span_type="CHAIN")
def review_saved_analysis(*, analysis_run: Path, output_dir: Path):
    result = SavedAnalysisReviewFlow(analysis_run=analysis_run, output_dir=output_dir).kickoff()
    ReviewResult.model_validate(result)
    return result
