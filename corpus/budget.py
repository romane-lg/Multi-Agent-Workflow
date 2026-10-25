"""Conservative context guard: preserve sources or stop, never silently truncate."""
import os
from pathlib import Path


def check_context(context, model):
    # Count actual input tokens; preserve full source text and reserve room for
    # task instructions, output schema and generated results.
    if model.startswith('gpt-4.1'):
        ceiling = 850_000
    elif model.startswith('gpt-4o-mini'):
        ceiling = 100_000
    else:
        raise ValueError('Full corpus model context limit is not configured; use gpt-4.1 or gpt-4o-mini with a sufficiently small corpus')
    import tiktoken
    os.environ.setdefault('TIKTOKEN_CACHE_DIR',str(Path(__file__).resolve().parents[1]/'.researcher/tokenizer_cache'))
    size = len(tiktoken.get_encoding('o200k_base').encode(context,disallowed_special=()))
    if size > ceiling:
        raise ValueError(f'Full context requires {size} tokens, over conservative {ceiling}-token bound for {model}. No source was truncated.')
    return size
