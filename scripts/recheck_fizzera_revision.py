"""Resume only a failed Reviewer recheck; never rerun the Analyst."""
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
    parser.add_argument("--revision-dir", type=Path, required=True)
    parser.add_argument("--review-output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.review_output_dir.exists():
        parser.error("Review output directory already exists")
    manifest = json.loads((args.revision_dir / "revision_manifest.json").read_text())
    if manifest["publication_status"] != "pending_review":
        parser.error("Resume is only available for an incomplete recheck")
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from analyst.revision import recheck_revision
    result = recheck_revision(args.revision_dir, args.review_output_dir)
    trace_id = mlflow.get_last_active_trace_id()
    mlflow.flush_trace_async_logging()
    trace = mlflow.get_trace(trace_id) if trace_id else None
    if trace is None or not trace.data.spans:
        raise RuntimeError("Recheck saved, but trace readback failed")
    result["recheck_trace_id"] = trace_id
    (args.revision_dir / "revision_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Persisted recheck trace:", trace_id, "spans:", len(trace.data.spans))


if __name__ == "__main__":
    main()
