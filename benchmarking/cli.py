"""CLI for human verification, frozen baseline runs, annotations and exports."""
import argparse
import json
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect")
    p.add_argument("benchmark", type=Path)
    p = sub.add_parser("freeze")
    p.add_argument("draft", type=Path)
    p.add_argument("--releases-dir", required=True, type=Path)
    p.add_argument("--version", required=True)
    p = sub.add_parser("run")
    p.add_argument("--benchmark", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--pricing", type=Path)
    p.add_argument("--task", action="append", help="Repeat to select a subset; omitted means entire release")
    p.add_argument("--repetitions", type=int)
    p.add_argument("--live", action="store_true")
    p = sub.add_parser("evaluation-template")
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--stage", default="final", choices=["initial", "final", "pre_recovery", "post_recovery"])
    p.add_argument("--output", required=True, type=Path)
    p = sub.add_parser("score")
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--evaluation", required=True, type=Path)
    p = sub.add_parser("export")
    p.add_argument("--experiment-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p = sub.add_parser("blind-export")
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        from benchmarking.benchmark import load_benchmark
        b = load_benchmark(args.benchmark)
        print(json.dumps({"version": b.version, "status": b.status,
            "tasks": [{"task_id": t.task_id, "verification_status": t.verification_status} for t in b.tasks]}, indent=2))
    elif args.command == "freeze":
        from benchmarking.benchmark import freeze_benchmark
        print(freeze_benchmark(args.draft, args.releases_dir, args.version))
    elif args.command == "run":
        if not args.live:
            parser.error("No experiment calls made. Add --live to authorize paid baseline experiments.")
        from benchmarking.runner import run_experiments
        config = read(args.config)
        if args.task is not None:
            config["task_ids"] = args.task
        if args.repetitions is not None:
            config["repetitions"] = args.repetitions
        print(json.dumps(run_experiments(benchmark_path=args.benchmark, config=config,
            output_dir=args.output_dir, live=True, pricing=read(args.pricing) if args.pricing else None)))
    elif args.command == "evaluation-template":
        from benchmarking.evaluation import evaluation_template
        from intelligence.workflow import save_json
        save_json(args.output, evaluation_template(args.run_dir, args.stage))
    elif args.command == "score":
        from benchmarking.evaluation import save_evaluation
        print(json.dumps(save_evaluation(args.run_dir, read(args.evaluation)), indent=2))
    elif args.command == "export":
        from benchmarking.export import export_results
        print(json.dumps(export_results(args.experiment_dir, args.output_dir), indent=2))
    else:
        from benchmarking.runner import export_blind_packet
        export_blind_packet(args.run_dir, args.output_dir)

if __name__ == "__main__":
    main()
