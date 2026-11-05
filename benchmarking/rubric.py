"""Independent human scoring. Never read the internal AI Reviewer's verdict."""
WEIGHTS = {"factual_accuracy": 30, "task_completeness": 25, "evidence_quality": 20,
           "claim_support": 15, "clarity_usefulness": 10}
ANCHORS = {
    "factual_accuracy": [
        "Central factual assertions are wrong or fabricated; no dependable answer.",
        "Several material errors undermine the main answer.",
        "Mixed accuracy; at least one material error or multiple minor inaccuracies.",
        "No material error; only minor imprecision that does not change conclusions.",
        "All assessed factual assertions match verified references, with correct dates, units and attribution."],
    "task_completeness": [
        "No required answer component is correctly addressed.",
        "Only a small minority of components are correctly addressed.",
        "About half of required components are correctly addressed; material gaps remain.",
        "Most components are correct; only a minor omission remains.",
        "Every required component is correctly addressed, including required abstentions and explicit gaps."],
    "evidence_quality": [
        "No inspectable evidence, fabricated sources, or entirely unsuitable sources.",
        "Evidence is mostly weak, stale, inaccessible without acknowledgement, or inappropriate.",
        "Some suitable sources, but important weaknesses in authority, date or independence.",
        "Mostly authoritative, relevant and dated sources with limited weaknesses disclosed.",
        "Appropriate authoritative frozen sources, provenance, dates and material limitations are preserved."],
    "claim_support": [
        "No factual claims are supported by the cited evidence, or citations are fabricated.",
        "Most material claims lack relevant supporting citations.",
        "Mixed support; some central claims have weak or mismatched evidence.",
        "All central claims are supported; only minor citation or qualification gaps.",
        "Every assessed factual claim is entailed by its cited evidence or explicitly and appropriately withheld."],
    "clarity_usefulness": [
        "Incoherent or unusable for the requested decision.",
        "Hard to follow; facts, assumptions and recommendations are frequently mixed.",
        "Understandable but vague, poorly organized or insufficiently qualified.",
        "Clear and useful with minor ambiguity or unnecessary detail.",
        "Precise, well organized and directly useful; facts, interpretation, proposals and uncertainties are distinct."]
}

def quality_score(scores):
    if set(scores) != set(WEIGHTS) or any(type(v) is not int or not 0 <= v <= 4 for v in scores.values()):
        raise ValueError("Supply each criterion exactly once with an integer from 0 to 4")
    return round(sum(WEIGHTS[k] * scores[k] / 4 for k in WEIGHTS), 6)
