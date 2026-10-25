"""Source-anchored sparse TF-IDF vectors; retrieval is a suggestion, never verification."""
from collections import Counter, defaultdict
import hashlib
import math
import re


def tokens(text):
    # Keep negations, numbers, currencies and brand names; no aggressive stemming.
    return re.findall(r"[\w]+(?:[.'’-][\w]+)*|[%$€£]", text.casefold())


def build_index(articles, max_words=240):
    if max_words < 1:
        raise ValueError('Chunk size must be positive')
    chunks, duplicates = [], defaultdict(list)
    for article in articles:
        if article['availability'] != 'full_text':
            continue
        normalized = ' '.join(' '.join(p['text'].split()) for p in article['paragraphs'])
        duplicates[hashlib.sha256(normalized.encode()).hexdigest()].append(article['article_id'])
        for p in article['paragraphs']:
            words = p['text'].split()
            for offset in range(0, len(words), max_words):
                chunks.append({'chunk_id': f"{article['article_id']}:{p['paragraph_id']}:{offset}",
                    'article_id': article['article_id'], 'paragraph_id': p['paragraph_id'],
                    'publication_date': article['publication_date'], 'url': article['url'],
                    'text_sha256': article['text_sha256'], 'word_offset': offset,
                    'text': ' '.join(words[offset:offset + max_words])})
    df = Counter(t for c in chunks for t in set(tokens(c['text'])))
    idf = {t: math.log((1 + len(chunks)) / (1 + n)) + 1 for t, n in df.items()}
    for chunk in chunks:
        counts = Counter(tokens(chunk['text']))
        values = {t: (1 + math.log(n)) * idf[t] for t, n in counts.items()}
        norm = math.sqrt(sum(v*v for v in values.values())) or 1
        chunk['vector'] = {t: v / norm for t, v in values.items()}
    return {'version': 'paragraph-tfidf-v1', 'idf': idf, 'chunks': chunks,
        'duplicate_bodies': [ids for ids in duplicates.values() if len(ids) > 1],
        'limits': 'Lexical similarity only; exact duplicate detection does not identify all syndicated events. No claim verification.'}


def search(index, query, limit=5, exclude_articles=()):
    counts = Counter(tokens(query))
    values = {t: (1 + math.log(n))*index['idf'][t] for t, n in counts.items() if t in index['idf']}
    norm = math.sqrt(sum(v*v for v in values.values())) or 1
    values = {t: v/norm for t, v in values.items()}
    hits = []
    for chunk in index['chunks']:
        if chunk['article_id'] in exclude_articles:
            continue
        score = sum(v * chunk['vector'].get(t, 0) for t, v in values.items())
        if score > 0:
            hits.append({**{k: v for k, v in chunk.items() if k != 'vector'}, 'similarity': round(score, 6)})
    return sorted(hits, key=lambda hit: (-hit['similarity'], hit['chunk_id']))[:limit]
