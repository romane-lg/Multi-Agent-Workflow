from __future__ import annotations

import argparse

from crew_ai.data import DEFAULT_DATASET_PATH
from crew_ai.framework import DEFAULT_MODEL, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CrewAI experiments on the frozen dataset.")
    parser.add_argument("--mode", choices=["single", "multi"], default="multi")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--output", default=None)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help="Optional article limit for quick tests. Omit for the full frozen dataset.",
    )
    args = parser.parse_args()

    output = args.output or f"outputs/{args.mode}_agent_report.md"
    run_experiment(
        mode=args.mode,
        dataset_path=args.dataset,
        output_path=output,
        model=args.model,
        max_articles=args.max_articles,
    )
    print(f"Saved {args.mode}-agent report to {output}")


if __name__ == "__main__":
    main()
