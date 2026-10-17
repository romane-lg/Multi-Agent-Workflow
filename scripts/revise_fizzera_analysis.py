"""Run exactly one Analyst correction cycle and Reviewer recheck on frozen evidence."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyst
from analyst.runtime import prepare_crewai_runtime
from researcher.runtime import configure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-run", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--issue-ids", nargs="+", help="Selected feedback IDs to assess")
    selection.add_argument("--all-issues", action="store_true", help="Assess all feedback; mistaken suggestions may be declined")
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists; use a new directory")
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from analyst.revision import revise_analysis
    ids = args.issue_ids
    if args.all_issues:
        review = json.loads((args.review_dir / "review_report.json").read_text())
        ids = [i["issue_id"] for i in review["assessment"]["issues"]]
    try:
        result = revise_analysis(analysis_run=args.analysis_run, review_dir=args.review_dir,
                                 output_dir=args.output_dir, issue_ids=ids)
        if not result or result.get("correction_attempt") != 1 or result.get("publication_status") == "pending_review":
            raise RuntimeError("Correction Flow did not complete the Reviewer recheck")
        trace_id = mlflow.get_last_active_trace_id()
        mlflow.flush_trace_async_logging()
        trace = mlflow.get_trace(trace_id) if trace_id else None
        if trace is None or not trace.data.spans:
            raise RuntimeError("Revision saved, but trace readback failed")
        result["trace_id"] = trace_id
        (args.output_dir / "revision_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
        print("Persisted correction trace:", trace_id, "spans:", len(trace.data.spans))
        print("Revised report:", args.output_dir / "analyst_report.md")
    except Exception as exc:
        if args.output_dir.is_dir():
            with (args.output_dir / "revision_failure.json").open("x") as handle:
                json.dump({"error_type": type(exc).__name__, "message": str(exc),
                           "publication_status": "hold_for_human_review", "automatic_retry": False,
                           "trace_id": mlflow.get_last_active_trace_id()}, handle, indent=2)
        raise


if __name__ == "__main__":
    main()
