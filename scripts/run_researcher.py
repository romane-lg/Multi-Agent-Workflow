"""Run one Researcher call on frozen local articles; no scraping or orchestration."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from researcher.runtime import LOCAL, configure, default_articles_path
from researcher.schema import QUESTION
from researcher.context import build_analyst_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--articles", type=Path, default=default_articles_path())
    parser.add_argument("--output", type=Path, default=LOCAL / "evidence_pack.json")
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--analyst-context", type=Path, help="Optional text handoff containing findings and complete source paragraphs")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; select a new --output path")
    context_path = args.analyst_context or args.output.with_suffix(".analyst.txt")
    if context_path.exists() or context_path.resolve() in (args.output.resolve(), args.articles.resolve()):
        parser.error("Analyst context output must be a new file distinct from input/output")
    articles = json.loads(args.articles.read_text())
    configure()
    from researcher.agent import research
    import mlflow
    result = research(question=args.question, articles=articles)
    trace_id = mlflow.get_last_active_trace_id()
    trace = mlflow.get_trace(trace_id) if trace_id else None
    if trace is None or not trace.data.spans:
        raise RuntimeError("No persisted trace found; fix tracing before evaluation")
    print("Persisted trace spans:", [(s.name, s.span_type) for s in trace.data.spans])
    result["run"]["trace_id"] = trace_id
    analyst_context = build_analyst_context(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    context_path.parent.mkdir(parents=True, exist_ok=True)
    with context_path.open("x") as handle:
        handle.write(analyst_context + "\n")
    print("Saved:", args.output)
    print("Analyst context:", context_path)
    print("Persisted trace:", trace_id)
    print("Findings:", len(result["evidence_pack"]["findings"]))
    print("Usage:", result["run"]["usage"])


if __name__ == "__main__":
    main()
