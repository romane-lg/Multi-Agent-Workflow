"""Fail-closed contracts; these tests do not measure model judgment accuracy."""
import copy
import unittest

from reviewer.evidence import focused_review_context, validate_fact_checks
from reviewer.schema import build_review_response_model, normalize_assessment
from reviewer.test_reviewer import inputs, live_response
from reviewer.validation import finalize_review


class EvidenceTests(unittest.TestCase):
    def test_live_schema_rejects_missing_sentence_or_risk_checks(self):
        data = live_response()
        del data['fact_checks']['fact_001']
        with self.assertRaises(ValueError):
            build_review_response_model(inputs()).model_validate(data)
        data = live_response()
        del data['risk_checks']['check_001']['chronology']
        with self.assertRaises(ValueError):
            build_review_response_model(inputs()).model_validate(data)

    def test_fabricated_quote_or_uncited_paragraph_is_rejected(self):
        data = live_response()['fact_checks']
        data['fact_001']['anchors'][0]['excerpt'] = 'This quotation does not exist in the frozen source.'
        with self.assertRaisesRegex(ValueError, 'excerpt'):
            validate_fact_checks(data, inputs())
        data = live_response()['fact_checks']
        data['fact_001']['anchors'][0]['paragraph_id'] = 'invented'
        with self.assertRaisesRegex(ValueError, 'cited evidence'):
            validate_fact_checks(data, inputs())

    def test_supported_without_anchor_rejected(self):
        data = live_response()['fact_checks']
        data['fact_001']['anchors'] = []
        with self.assertRaisesRegex(ValueError, 'anchors'):
            validate_fact_checks(data, inputs())

    def test_partial_support_forces_hold_even_with_empty_model_issue_lists(self):
        data = live_response()
        data['fact_checks']['fact_001'].update(verdict='partial', required_correction='Remove the unsupported second brand.')
        value = normalize_assessment(data, inputs())
        self.assertEqual(finalize_review(value, inputs(), {}).publication_status, 'hold_for_human_review')

    def test_risk_failure_forces_blocking_issue(self):
        data = live_response()
        data['risk_checks']['check_001']['chronology'].update(status='issue',
            explanation='A 2024 decline cannot demonstrate that a 2026 campaign failed.', required_correction='Separate periods and remove causal inference.')
        value = normalize_assessment(data, inputs())
        self.assertEqual(finalize_review(value, inputs(), {}).overall_verdict, 'fail')
        self.assertEqual(value.issues[0].category, 'temporal_context')

    def test_persisted_checks_cannot_be_separated_from_blocking_verdict(self):
        data = live_response()
        data['fact_checks']['fact_001'].update(verdict='unsupported', required_correction='Remove the claim.')
        run = {'evidence_policy': 'sentence-anchors-and-item-risks-v1',
               'evidence_checks': {'fact_checks': data['fact_checks'], 'risk_checks': data['risk_checks']}}
        value = normalize_assessment(live_response(), inputs())
        with self.assertRaisesRegex(ValueError, 'cannot be omitted'):
            finalize_review(value, inputs(), run)

    def test_focused_context_includes_original_body_and_marks_search_as_unverified(self):
        context = focused_review_context(inputs())
        text = inputs()['upstream_handoff']['researcher_output']['sources'][0]['paragraphs'][0]['text']
        self.assertIn(text, context)
        self.assertIn('supplementary_search_hits_not_corroboration', context)
        self.assertIn('required_sentence_checks', context)


if __name__ == '__main__':
    unittest.main()
