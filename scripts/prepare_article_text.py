"""Create a new clean snapshot, paragraph vector index and complete cleanup ledger."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus.text import clean_articles, refresh_research_sources
from corpus.index import build_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--articles', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--researcher-output', type=Path, help='Reuse existing findings only if the exact cleaned sources preserve every citation')
    args = parser.parse_args()
    articles, audit = clean_articles(json.loads(args.articles.read_text()))
    index = build_index(articles)
    research = refresh_research_sources(json.loads(args.researcher_output.read_text()), articles) if args.researcher_output else None
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, value in [('articles.json', articles), ('cleanup_audit.json', audit), ('text_index.json', index)]:
        (args.output_dir/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    if research:
        (args.output_dir/'researcher_output.json').write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Sources:', len(articles), 'chunks:', len(index['chunks']), 'changed paragraphs:', sum(len(a['changes']) for a in audit['articles']))


if __name__ == '__main__':
    main()
