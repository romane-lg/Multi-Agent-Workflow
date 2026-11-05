"""Pure contracts shared by legacy and paired one-cycle corrections."""
import difflib
import json
from typing import Literal
from pydantic import create_model
from researcher.schema import StrictModel

class FeedbackResponse(StrictModel):
    disposition: Literal["addressed", "declined", "needs_evidence"]
    rationale: str
    change_description: str

def revision_response_model(issues, report_model=None):
    if report_model is None:
        from analyst.schema import AnalystReport
        report_model = AnalystReport
    responses = create_model("RequiredRevisionResponses", __base__=StrictModel,
                             **{i["issue_id"]: (FeedbackResponse, ...) for i in issues})
    return create_model("AnalystRevision", __base__=StrictModel,
                        report=(report_model, ...), feedback_responses=(responses, ...))

def report_diff(original: dict, revised: dict) -> str:
    """Code-generated comparison, independent of the model's claimed change log."""
    return "".join(difflib.unified_diff(
        (json.dumps(original, ensure_ascii=False, sort_keys=True, indent=2) + "\n").splitlines(keepends=True),
        (json.dumps(revised, ensure_ascii=False, sort_keys=True, indent=2) + "\n").splitlines(keepends=True),
        fromfile="original/analyst_report.json", tofile="revision/analyst_report.json"))
