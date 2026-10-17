"""Offline validation of the frozen evidence supplied to both architectures."""
import copy
import unittest

from crew_ai.data import build_article_context, load_dataset, selected_articles


class ArticleContextTests(unittest.TestCase):
    def test_lau_dataset_filters_before_limit(self):
        dataset = load_dataset()
        accepted = selected_articles(dataset)
        self.assertEqual(len(accepted), 255)
        self.assertTrue(all(a['eligibility_status'] == 'accepted' for a in accepted))
        rejected = next(a for a in dataset['articles'] if a['eligibility_status'] == 'rejected')
        mixed = {**dataset, 'articles': [rejected, accepted[0]]}
        context = build_article_context(mixed, max_articles=1)
        self.assertIn(accepted[0]['normalized_url'], context)
        self.assertNotIn(rejected['normalized_url'], context)
        self.assertIn('title-level evidence only', context)

    def test_company_evidence_and_text_preserved_without_mutation(self):
        article = {
            'title': 'Shared launch', 'normalized_url': 'https://example.com/shared',
            'eligibility_status': 'accepted', 'article_text': 'Extracted evidence.',
            'discovery_associations': [
                {'decision': 'accepted', 'matched_companies': ['Poppi', 'Olipop'], 'discovery_dimension': 'products'},
                {'decision': 'rejected', 'matched_companies': ['Zevia'], 'discovery_dimension': 'business'},
            ],
        }
        dataset = {'schema_version': '2.0', 'articles': [article]}
        original = copy.deepcopy(dataset)
        context = build_article_context(dataset)
        self.assertIn('Confirmed companies: Olipop, Poppi', context)
        self.assertNotIn('Zevia', context)
        self.assertIn('Extracted evidence.', context)
        self.assertIn('provenance only', context)
        self.assertEqual(dataset, original)

    def test_old_dataset_supported(self):
        dataset = load_dataset('news_scrapper/news_dataset.json')
        context = build_article_context(dataset, max_articles=1)
        self.assertIn(dataset['articles'][0]['link'], context)


if __name__ == '__main__':
    unittest.main()
