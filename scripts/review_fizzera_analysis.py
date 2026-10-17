"""Review a frozen Analyst run without rerunning or modifying the upstream agents."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyst  # Project-local CrewAI runtime configuration, before framework imports.
from analyst.runtime import prepare_crewai_runtime
from researcher.runtime import configure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not all((args.analysis_run / name).is_file() for name in ("handoff.json", "analyst_report.json")):
        parser.error("Analysis run must contain handoff.json and analyst_report.json")
    if args.output_dir.exists():
        parser.error("Review output directory exists; use a new directory")
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from reviewer.workflow import review_saved_analysis
    result = review_saved_analysis(analysis_run=args.analysis_run, output_dir=args.output_dir)
    trace_id = mlflow.get_last_active_trace_id()
    print("Review trace ID:", trace_id, flush=True)
    mlflow.flush_trace_async_logging()
    trace = mlflow.get_trace(trace_id) if trace_id else None
    if trace is None or not trace.data.spans:
        raise RuntimeError("Review saved, but trace readback failed")
    print("Persisted trace spans:", [(s.name, s.span_type) for s in trace.data.spans])
    manifest = {
        "workflow": "CrewAI saved-analysis handoff -> independent Reviewer",
        "analysis_run": str(args.analysis_run), "trace_id": trace_id,
        "verdict": result["overall_verdict"], "publication_status": result["publication_status"],
        "input_hashes": result["input_hashes"], "reviewer_run": result["run"],
        "researcher_rerun": False, "analyst_rerun": False,
    }
    with (args.output_dir / "review_manifest.json").open("x") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
