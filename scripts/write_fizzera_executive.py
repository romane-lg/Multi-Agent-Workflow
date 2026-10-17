"""Create a short, styled executive brief from an existing reviewed analysis."""
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
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists; use a new directory")
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from executive.workflow import write_executive_brief
    try:
        result = write_executive_brief(analysis_run=args.analysis_run, review_dir=args.review_dir, output_dir=args.output_dir)
        trace_id = mlflow.get_last_active_trace_id()
        mlflow.flush_trace_async_logging()
        trace = mlflow.get_trace(trace_id) if trace_id else None
        if trace is None or not trace.data.spans:
            raise RuntimeError("Executive brief saved, but trace readback failed")
        result["trace_id"] = trace_id
        (args.output_dir / "executive_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
        print("Persisted executive trace:", trace_id, "spans:", len(trace.data.spans))
    except Exception as exc:
        if args.output_dir.is_dir():
            with (args.output_dir / "failure.json").open("x") as handle:
                json.dump({"error_type": type(exc).__name__, "message": str(exc),
                           "presentation_status": "failed", "trace_id": mlflow.get_last_active_trace_id()}, handle, indent=2)
        raise


if __name__ == "__main__":
    main()
