"""Regression contracts for cleanup, citation integrity and lexical retrieval."""
import copy
import hashlib
import unittest

from corpus.index import build_index, search
from corpus.text import clean_articles, refresh_research_sources, repair_encoding
from analyst.test_workflow import evidence


def source(paragraphs):
    article = copy.deepcopy(evidence()['sources'][0])
    article['paragraphs'] = [{'paragraph_id': f'p{i}', 'text': text} for i, text in enumerate(paragraphs, 1)]
    article['text_sha256'] = hashlib.sha256('\n\n'.join(paragraphs).encode()).hexdigest()
    return article


class TextTests(unittest.TestCase):
    def test_cleaner_keeps_negation_numbers_and_original_ids(self):
        original = source(['Share', 'Poppi did not report Ontario growth; revenue fell 6.8% in 2024.',
                           'RECOMMENDED READING', 'An unrelated story about a different brand.'])
        before = copy.deepcopy(original)
        cleaned, audit = clean_articles([original])
        self.assertEqual(cleaned[0]['paragraphs'], [original['paragraphs'][1]])
        self.assertEqual(cleaned[0]['paragraphs'][0]['paragraph_id'], 'p2')
        self.assertEqual(original, before)
        self.assertEqual(len(audit['articles'][0]['changes']), 3)

    def test_encoding_repairs_preserve_factual_content(self):
        text = 'Zeviaâ€™s â€œrealâ€ soda grew 21.2%; café prices were CAD $2.99.'
        self.assertEqual(repair_encoding(text), 'Zevia’s “real” soda grew 21.2%; café prices were CAD $2.99.')
        self.assertEqual(repair_encoding('“Not proven” is not “proven”.'), '“Not proven” is not “proven”.')

    def test_cleanup_is_idempotent_and_flags_unrecoverable_encoding(self):
        a = source(['Cove\u200b has no verified Ontario result. Damaged character: \ufffd'])
        clean, audit = clean_articles([a])
        self.assertTrue(audit['articles'][0]['unresolved_encoding'])
        self.assertEqual(clean_articles(clean)[0], clean)

    def test_cleanup_cannot_reuse_findings_whose_citation_was_removed(self):
        result = evidence()
        result['sources'] = [source(['Share', 'Substantive retained source text.'])]
        cleaned, _ = clean_articles(result['sources'])
        with self.assertRaisesRegex(ValueError, 'unknown paragraph'):
            refresh_research_sources(result, cleaned)

    def test_vector_chunks_retain_provenance_and_number_tokens(self):
        a = source(['Cove announced Walmart Canada distribution.', 'Zevia did not report 21.2% Ontario growth.'])
        index = build_index([a], max_words=5)
        hits = search(index, 'Cove Walmart Canada')
        self.assertEqual(hits[0]['paragraph_id'], 'p1')
        self.assertEqual(hits[0]['text_sha256'], a['text_sha256'])
        self.assertIn('not', index['idf'])
        self.assertIn('21.2', index['idf'])
        self.assertTrue(all(len(c['text'].split()) <= 5 for c in index['chunks']))

    def test_duplicate_bodies_flagged_without_dropping_articles(self):
        a = source(['A genuine repeated press release about Cove.'])
        b = {**copy.deepcopy(a), 'article_id': 'duplicate'}
        index = build_index([a, b])
        self.assertEqual(index['duplicate_bodies'], [[a['article_id'], 'duplicate']])
        self.assertEqual(len(index['chunks']), 2)
        self.assertFalse(search(index, 'unmatchedword'))


if __name__ == '__main__':
    unittest.main()
