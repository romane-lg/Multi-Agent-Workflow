"""Merge reviewed public-reader bodies into a NEW frozen source snapshot."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from researcher.runtime import LOCAL
from researcher.sources import apply_reader_supplement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=LOCAL / "articles.json")
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=LOCAL / "articles_rechecked.json")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new snapshot filename")
    articles = apply_reader_supplement(json.loads(args.input.read_text()), json.loads(args.supplement.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(articles, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    for article in articles:
        print(article["article_id"], article["availability"], sum(len(p["text"].split()) for p in article["paragraphs"]), "words", article["retrieval_method"])


if __name__ == "__main__":
    main()
