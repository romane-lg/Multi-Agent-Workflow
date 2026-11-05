"""Run User query -> Planner -> Researcher -> Analyst -> Reviewer -> Output."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--company", action="append", default=[], help="Repeat for each company")
    parser.add_argument("--articles", type=Path, required=True, help="Frozen Article JSON array, not discovery URLs")
    parser.add_argument("--company-context", type=Path, help="Optional JSON object of named planning-context strings")
    parser.add_argument("--period", help="Requested research period; included in the Planner input")
    parser.add_argument("--as-of", default=datetime.now(ZoneInfo("America/Toronto")).date().isoformat())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--live", action="store_true", help="Explicitly authorize paid model calls")
    args = parser.parse_args()
    if not args.live:
        parser.error("No calls made. Add --live to explicitly enable paid model calls.")
    from intelligence.workflow import run_workflow
    state = run_workflow(query={"question": args.question, "companies": args.company,
        "as_of_date": args.as_of, "period": args.period,
        "company_context": json.loads(args.company_context.read_text(encoding="utf-8")) if args.company_context else {}},
        articles=json.loads(args.articles.read_text(encoding="utf-8")),
        output_dir=args.output_dir, batch_size=args.batch_size, live=True)
    print(json.dumps(state, indent=2))

if __name__ == "__main__":
    main()
