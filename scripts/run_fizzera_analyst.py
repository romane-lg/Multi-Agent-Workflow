"""Run the Researcher-to-Analyst collaboration under CrewAI orchestration."""
import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyst  # Set local CrewAI storage/tracing policy before MLflow loads its integration.
from analyst.runtime import prepare_crewai_runtime
from researcher.runtime import LOCAL, configure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--as-of", default=datetime.now(ZoneInfo("America/Toronto")).date().isoformat())
    parser.add_argument("--review", action="store_true", help="Run the independent Reviewer after the Analyst, with no automatic corrections")
    parser.add_argument("--executive", action="store_true", help="Run Reviewer then the final executive presentation agent; implies --review")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--research-output", type=Path)
    source.add_argument("--articles", type=Path, help="Run the existing Researcher first on this frozen snapshot")
    args = parser.parse_args()
    try:
        date.fromisoformat(args.as_of)
    except ValueError:
        parser.error("--as-of must be YYYY-MM-DD")
    research_path = args.research_output
    if research_path is None and args.articles is None:
        research_path = LOCAL / "evidence_pack_expanded.json"
    if not args.brief.is_file() or not (research_path or args.articles).is_file():
        parser.error("Company brief and selected Researcher output/article snapshot must exist")
    if args.output_dir.exists():
        parser.error("Output directory exists; choose a new directory to preserve previous runs")
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from analyst.workflow import run_workflow
    args.output_dir.mkdir(parents=True)
    try:
        run_workflow(brief_path=args.brief, output_dir=args.output_dir,
                     as_of_date=args.as_of, research_output_path=research_path, articles_path=args.articles,
                     review=args.review, executive=args.executive)
    except Exception as exc:
        (args.output_dir / "failure.json").write_text(json.dumps({"error_type": type(exc).__name__, "trace_id": mlflow.get_last_active_trace_id()}))
        raise
    trace_id = mlflow.get_last_active_trace_id()
    print("Trace ID:", trace_id, flush=True)
    mlflow.flush_trace_async_logging()
    trace = mlflow.get_trace(trace_id) if trace_id else None
    if trace is None or not trace.data.spans:
        raise RuntimeError("Output saved, but MLflow trace readback did not succeed")
    print("Persisted trace spans:", [(s.name, s.span_type) for s in trace.data.spans])
    manifest_path = args.output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["trace_id"] = trace_id
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Report:", args.output_dir / "analyst_report.md")
    if args.review or args.executive:
        print("Review:", args.output_dir / "review" / "review_report.md")
        print("Publication status:", manifest["publication_status"])
    if args.executive:
        print("Executive brief:", args.output_dir / "executive" / "executive_brief.html")


if __name__ == "__main__":
    main()
