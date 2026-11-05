"""V1/V2 offline experiments with synthetic sources and mocked editor/auditor."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from benchmarking.test_phase1 import fixture_release, BenchmarkBackend
from benchmarking.benchmark import file_hash
from intelligence.test_workflow import sources
from intelligence.runtime import StageResult
from intelligence.workflow import save_json
from benchmarking.paired import prepare_pair, run_variant, load_pair
from benchmarking.recovery import correct_once, merge_evidence
from benchmarking.experimental_schema import MAX_RETRIES

class PairedBackend(BenchmarkBackend):
    def __init__(self, failure=None, target="analyst", second_fail=False, audit_fail=False):
        super().__init__()
        self.failure, self.target = failure, target
        self.second_fail, self.audit_fail = second_fail, audit_fail

    def generate(self, stage, schema, instructions, payload):
        if stage == "executive":
            self.calls.append(stage)
            card={"implication":"Evidence remains conditional.", "action":"Review the task evidence before deciding.",
                  "metric_or_gate":"Obtain decision-specific evidence.", "caveat":"The historical sample has limitations."}
            data={"strategic_outlook":"Use the supported task evidence while preserving uncertainty.",
                "priority_focuses":["ontario_retail","pricing","product_launch"],
                "market_signals":[{"text":"The source reports a feature announcement.","insight_ids":["i1"]},
                                  {"text":"An announcement does not establish commercial outcomes.","insight_ids":["i1"]}],
                "topics":{focus:card for focus in ("ontario_retail","pricing","product_launch","marketing","bc_expansion")}}
        elif stage == "editorial_auditor":
            self.calls.append(stage)
            a=next(a for a in payload["sources"] if a["availability"]=="full_text")
            data={key:{"verdict":"supported","explanation":"Synthetic exact-anchor check.",
                "source_anchors":[{"article_id":a["article_id"],"paragraph_id":a["paragraphs"][0]["paragraph_id"],
                    "excerpt":a["paragraphs"][0]["text"]}],"brief_anchors":[],"required_correction":""}
                for key in schema.model_fields}
            if self.audit_fail:
                data["outlook"].update(verdict="needs_correction",required_correction="Narrow the outlook.")
        elif stage=="analyst" and "report" in schema.model_fields:
            self.calls.append(stage)
            data={"report":payload["original_report"],"feedback_responses":{
                issue["issue_id"]:{"disposition":"declined","rationale":"The synthetic source supports the original claim.",
                    "change_description":"Retained the supported original wording; criticism disputed."}
                for issue in payload["selected_issues"]}}
        else:
            result=super().generate(stage,schema,instructions,payload)
            data=result.data
            if stage=="analyst":
                for i in data["insights"]:
                    i["context_keys"]=["BRIEF p9"]
            if stage=="reviewer":
                is_second="selected_issues" in payload
                if self.failure and (not is_second or self.second_fail):
                    data["items"][0].update(disposition="needs_correction",
                        explanation="Missing fixture feature evidence.",required_correction="Check the scoped feature evidence.",
                        failure_type=self.failure,severity="high",target_agent=self.target,
                        information_status="missing" if self.target=="researcher" else "available")
                if is_second:
                    data["feedback_resolution"]={issue["issue_id"]:{
                        "status":"unresolved" if self.second_fail else "resolved",
                        "explanation":"Synthetic independent recheck."} for issue in payload["selected_issues"]}
        return StageResult(data,json.dumps(data),"mock-model",
            {"prompt_tokens":10,"completion_tokens":5,"total_tokens":15,"successful_requests":1},
            model_calls=1,tool_calls=0)

def prepare_fixture(root, backend=None, supplement=False):
    root=Path(root)
    benchmark=fixture_release(root)
    pages=[{"page_number":i,"text":f"Synthetic planning context for page {i}. No verified market facts."} for i in range(1,19)]
    text="\n\f\n".join(p["text"] for p in pages)
    brief={"company_name":"Fizzera","source_filename":"synthetic-fixture.pdf","pdf_sha256":"0"*64,
        "text_sha256":hashlib.sha256(text.encode()).hexdigest(),"pages":pages,
        "data_status_notes":["Synthetic unit-test fixture."],
        "investment_envelope_cad":1200000,"product_launch_budget_cad":250000}
    save_json(root/"brief.json",brief)
    config={"benchmark_version":"test-v1","brief":{"path":"brief.json","sha256":file_hash(root/"brief.json")}}
    if supplement:
        extra=sources()
        extra[0]["article_id"]="a-extra"
        save_json(root/"extra.json",extra)
        config["supplemental_evidence"]={"T01":{"path":"extra.json","sha256":file_hash(root/"extra.json")}}
    pair=root/"pair"
    prepare_pair(benchmark_path=benchmark,task_id="T01",config=config,config_root=root,
        output_dir=pair,backend_factory=lambda:backend or PairedBackend())
    return pair

class PairedTests(unittest.TestCase):
    def test_v1_never_recovers_even_with_material_failure(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("unsupported_claim"))
            backend=PairedBackend()
            run=run_variant(pair_dir=pair,version="sequential_v1",backend_factory=lambda:backend)
            self.assertEqual(backend.calls,["executive","editorial_auditor"])
            self.assertEqual(run["recovery_attempts"],0)
            self.assertEqual(run["publication_status"],"hold_for_human_review")

    def test_v2_reuses_initial_review_and_runs_one_analyst_reviewer_correction(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("unsupported_claim"))
            backend=PairedBackend()
            initial=file_hash(pair/"shared/analyst_report.json")
            a=run_variant(pair_dir=pair,version="sequential_v1",backend_factory=PairedBackend)
            b=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertEqual(backend.calls,["analyst","reviewer","executive","editorial_auditor"])
            self.assertEqual(b["recovery_attempts"],1)
            self.assertEqual(a["shared_review_sha256"],b["shared_review_sha256"])
            self.assertEqual(a["shared_analyst_sha256"],b["shared_analyst_sha256"])
            self.assertEqual(file_hash(pair/"shared/analyst_report.json"),initial)
            self.assertIn("pre_recovery",b["report_artifacts"])
            self.assertIn("post_recovery",b["report_artifacts"])
            self.assertEqual(b["status"],"completed")
            self.assertTrue((pair/"runs"/b["run_id"]/"workflow/recovery_result.json").exists())

    def test_v2_stops_after_second_failed_review(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("geography"))
            backend=PairedBackend("geography",second_fail=True)
            run=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertEqual(backend.calls.count("reviewer"),1)
            self.assertEqual(backend.calls.count("analyst"),1)
            self.assertEqual(run["publication_status"],"hold_for_human_review")
            self.assertEqual(run["recovery_attempts"],MAX_RETRIES)

    def test_targeted_research_uses_only_new_scoped_sources(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("missing_information",target="researcher"),supplement=True)
            backend=PairedBackend()
            run=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertEqual(backend.calls,["researcher","analyst","reviewer","executive","editorial_auditor"])
            folder=pair/"runs"/run["run_id"]/"workflow"
            evidence=json.loads((folder/"updated_evidence.json").read_text())
            original=json.loads((pair/"shared/researcher_output.json").read_text())
            self.assertEqual(evidence["findings"][:len(original["findings"])],original["findings"])
            self.assertEqual(len(evidence["sources"]),2)
            self.assertEqual(evidence["sources"][0],original["sources"][0])
            request=json.loads((folder/"stage_0001_researcher_input.json").read_text())
            self.assertEqual([a["article_id"] for a in request["articles"]],["a-extra"])

    def test_missing_supplement_does_not_repeat_entire_corpus(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("missing_information",target="researcher"))
            backend=PairedBackend()
            run=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertNotIn("researcher",backend.calls)
            self.assertEqual(backend.calls.count("analyst"),1)

    def test_formatting_failure_never_triggers_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root,PairedBackend("formatting"))
            backend=PairedBackend()
            run=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertFalse(run["recovery_triggered"])
            self.assertEqual(backend.calls,["executive","editorial_auditor"])

    def test_final_audit_failure_holds_initial_pass(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root)
            run=run_variant(pair_dir=pair,version="sequential_v1",
                            backend_factory=lambda:PairedBackend(audit_fail=True))
            self.assertEqual(run["reviewer_verdict"],"pass")
            self.assertEqual(run["publication_status"],"hold_for_human_review")
            self.assertFalse(run["editorial_audit_passed"])

    def test_second_correction_is_rejected_before_any_call(self):
        with self.assertRaisesRegex(ValueError,"MAX_RETRIES"):
            correct_once(query=None,plan=None,evidence=None,report=None,review=None,
                supplemental=[],call=None,save=None,validate_fizzera=None,attempt=2)

    def test_shared_evidence_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root)
            (pair/"shared/analyst_report.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"Shared input"):
                run_variant(pair_dir=pair,version="sequential_v1",backend_factory=PairedBackend)

    def test_unchanged_pass_in_v2_does_not_call_analyst_or_reviewer_again(self):
        with tempfile.TemporaryDirectory() as root:
            pair=prepare_fixture(root)
            backend=PairedBackend()
            run=run_variant(pair_dir=pair,version="targeted_recovery_v2",backend_factory=lambda:backend)
            self.assertEqual(run["recovery_attempts"],0)
            self.assertEqual(backend.calls,["executive","editorial_auditor"])

if __name__=="__main__":
    unittest.main()
