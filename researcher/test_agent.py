"""Functional checks only: no model calls, judge calls, or quality scores."""
import hashlib
import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from researcher.agent import research, validate_pack
from researcher.schema import Article, EvidencePack, QUESTION
from researcher.context import build_analyst_context
from researcher.sources import apply_reader_supplement


def source():
    text = "Poppi announced a new flavor."
    return Article(
        article_id="a1", title="Flavor announcement", url="https://example.com/article",
        publication_date="2025-01-01", availability="full_text", access_note="test fixture",
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        paragraphs=[{"paragraph_id": "p1", "text": text}],
    )


def pack():
    return EvidencePack.model_validate({
        "question": QUESTION,
        "article_assessments": [{"article_id": "a1", "relevance": "high", "summary": "New flavor announced.", "reason": "Product news."}],
        "findings": [{
            "finding_id": "f1", "claim": "Poppi announced a new flavor.", "publication_date": "2025-01-01",
            "companies": ["Poppi"], "dimension": "products", "evidence_type": "competitor_action",
            "attribution": "Article", "effectiveness": "not_measured", "limitations": "No sales data.",
            "citations": [{"article_id": "a1", "paragraph_id": "p1"}],
        }],
        "company_coverage": [{"company": c, "finding_ids": ["f1"] if c == "Poppi" else [], "gap": "No outcome evidence."}
                             for c in ("Olipop", "Poppi", "Culture Pop", "Zevia")],
        "limitations": ["Small sample."],
    })


class ResearcherTests(unittest.TestCase):
    def test_valid_pack_and_source_unchanged(self):
        article = source()
        original = article.model_dump()
        validate_pack(pack(), [article], QUESTION)
        self.assertEqual(original, article.model_dump())

    def test_rejects_invented_citation(self):
        evidence = pack()
        evidence.findings[0].citations[0].paragraph_id = "made-up"
        with self.assertRaisesRegex(ValueError, "unknown paragraph"):
            validate_pack(evidence, [source()], QUESTION)

    def test_rejects_wrong_date(self):
        evidence = pack()
        evidence.findings[0].publication_date = "2026-01-01"
        with self.assertRaisesRegex(ValueError, "publication date"):
            validate_pack(evidence, [source()], QUESTION)

    def test_rejects_unsupported_coverage(self):
        evidence = pack()
        evidence.company_coverage[0].finding_ids = ["f1"]
        with self.assertRaisesRegex(ValueError, "coverage"):
            validate_pack(evidence, [source()], QUESTION)

    def test_rejects_causal_label_in_observational_pilot(self):
        data = pack().model_dump()
        data["findings"][0]["effectiveness"] = "causal_evidence"
        with self.assertRaises(ValidationError):
            EvidencePack.model_validate(data)

    def test_unavailable_article_handled_in_code(self):
        unavailable = source().model_copy(update={
            "article_id": "a2", "availability": "unavailable", "paragraphs": [],
            "text_sha256": hashlib.sha256(b"").hexdigest(), "access_note": "access denied",
        })
        fake_response = MagicMock(output_parsed=pack(), model="test", id="test-response")
        fake_response.usage = None
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}), patch("researcher.agent.OpenAI") as client:
            client.return_value.responses.parse.return_value = fake_response
            result = research.__wrapped__(QUESTION, [source().model_dump(), unavailable.model_dump()])
            self.assertEqual(result["evidence_pack"]["article_assessments"][-1]["relevance"], "unavailable")
            self.assertEqual(result["sources"][0]["paragraphs"], source().model_dump()["paragraphs"])
            request = client.return_value.responses.parse.call_args.kwargs["input"][1]["content"]
            self.assertNotIn('"article_id": "a2"', request)
            client.return_value.responses.parse.assert_called_once()

    def test_rejects_modified_source_before_model_call(self):
        article = source().model_dump()
        article["paragraphs"][0]["text"] = "Changed content."
        with patch("researcher.agent.OpenAI") as client, self.assertRaisesRegex(ValueError, "hash"):
            research.__wrapped__(QUESTION, [article])
        client.assert_not_called()

    def test_analyst_receives_complete_uncited_paragraphs(self):
        article = source().model_dump()
        article["paragraphs"].append({"paragraph_id": "p2", "text": "Extra context beyond the short summary. " * 250})
        full_text = "\n\n".join(p["text"] for p in article["paragraphs"])
        article["text_sha256"] = hashlib.sha256(full_text.encode()).hexdigest()
        result = {"evidence_pack": pack().model_dump(), "sources": [article]}
        context = build_analyst_context(result)
        self.assertIn(article["paragraphs"][1]["text"], context)
        self.assertIn("[a1:p2]", context)
        self.assertIn(article["url"], context)

    def test_analyst_rejects_stale_text(self):
        article = source().model_dump()
        article["paragraphs"][0]["text"] = "Changed content."
        with self.assertRaisesRegex(ValueError, "hash"):
            build_analyst_context({"evidence_pack": pack().model_dump(), "sources": [article]})

    def test_reader_import_restores_missing_article_without_changing_old_snapshot(self):
        article = source().model_dump()
        article.update(availability="unavailable", paragraphs=[], text_sha256=hashlib.sha256(b"").hexdigest())
        body = "Publicly readable article body with substantial context. " * 25
        supplement = [{"article_id": "a1", "retrieval_method": "public_web_reader",
                       "retrieved_at": "2026-10-16T23:00:00Z", "paragraphs": [{"text": body}]}]
        result = apply_reader_supplement([article], supplement)
        self.assertEqual(result[0]["availability"], "full_text")
        self.assertEqual(result[0]["paragraphs"][0]["text"], body.strip())
        self.assertEqual(result[0]["url"], article["url"])
        self.assertEqual(result[0]["retrieval_method"], "public_web_reader")
        self.assertEqual(article["availability"], "unavailable")
        self.assertEqual(article["paragraphs"], [])

    def test_reader_import_rejects_title_only_snippet(self):
        article = source().model_dump()
        article.update(availability="unavailable", paragraphs=[])
        with self.assertRaisesRegex(ValueError, "too short"):
            apply_reader_supplement([article], [{"article_id": "a1", "paragraphs": [{"text": "A short headline."}]}])

    def test_no_content_rejected_before_model_call(self):
        article = source().model_dump()
        article.update(availability="unavailable", paragraphs=[])
        with patch("researcher.agent.OpenAI") as client, self.assertRaisesRegex(ValueError, "No accessible"):
            research.__wrapped__(QUESTION, [article])
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
