"""Metrics from independent annotations, never AI assertions as truth."""
def ratio(numerator, denominator):
    if type(numerator) is not int or type(denominator) is not int or numerator < 0 or denominator < 0:
        raise ValueError("Counts must be nonnegative integers")
    return None if denominator == 0 else numerator / denominator

def unsupported_claim_rate(unsupported, total):
    if unsupported > total:
        raise ValueError("Unsupported claims exceed total claims")
    return ratio(unsupported, total)

def error_detection_precision(true_positive_flags, total_flags):
    if true_positive_flags > total_flags:
        raise ValueError("True-positive flags exceed all flags")
    return ratio(true_positive_flags, total_flags)

def error_detection_recall(detected_errors, verified_errors):
    if detected_errors > verified_errors:
        raise ValueError("Detected errors exceed verified errors")
    return ratio(detected_errors, verified_errors)

def task_completeness(correct_components, required_components):
    if correct_components > required_components:
        raise ValueError("Correct components exceed required components")
    return ratio(correct_components, required_components)

def recovery_success_rate(resolved_cases, total_cases):
    if resolved_cases > total_cases:
        raise ValueError("Resolved cases exceed recovery cases")
    return ratio(resolved_cases, total_cases)

def error_reduction_rate(before, after):
    ratio(after, before)  # Validate counts; a negative reduction means errors increased.
    return None if before == 0 else (before - after) / before

def annotation_metrics(evaluation, task):
    required = {c.component_id for c in task.expected_components}
    components = {c.component_id: c for c in evaluation.components}
    if not set(components) <= required:
        raise ValueError("Annotation references an unknown required component")
    if evaluation.component_inventory_complete and set(components) != required:
        raise ValueError("Complete component inventory must include every required component")
    facts = {f.fact_id for f in task.reference_facts}
    if any(not set(c.reference_fact_ids) <= facts for c in evaluation.claims):
        raise ValueError("Claim annotation references unknown benchmark facts")
    if evaluation.error_inventory_complete:
        erroneous = {c.claim_id for c in evaluation.claims
                     if c.accuracy == "incorrect" or c.support == "unsupported"}
        linked = {e.claim_id for e in evaluation.verified_errors}
        missing = {c.component_id for c in evaluation.components if c.verdict == "missing"}
        linked_components = {e.component_id for e in evaluation.verified_errors}
        if not erroneous <= linked or not missing <= linked_components:
            raise ValueError("Complete error inventory must account for annotated incorrect/unsupported claims and missing components")
    matched = {f.matched_error_id for f in evaluation.reviewer_flags if f.matched_error_id is not None}
    verified = {e.error_id for e in evaluation.verified_errors}
    results = {
        "unsupported_claim_rate": unsupported_claim_rate(
            sum(c.support == "unsupported" for c in evaluation.claims), len(evaluation.claims))
            if evaluation.claim_inventory_complete else None,
        "error_detection_precision": error_detection_precision(
            sum(f.matched_error_id is not None for f in evaluation.reviewer_flags),
            len(evaluation.reviewer_flags)) if evaluation.error_inventory_complete else None,
        "error_detection_recall": error_detection_recall(len(matched), len(verified))
            if evaluation.error_inventory_complete else None,
        "task_completeness": task_completeness(
            sum(c.verdict == "correct" for c in components.values()), len(required))
            if evaluation.component_inventory_complete else None,
        "recovery_success_rate": recovery_success_rate(
            sum(set(c.target_error_ids) <= set(c.resolved_error_ids) for c in evaluation.recovery_cases),
            len(evaluation.recovery_cases)),
        "error_reduction_rate": error_reduction_rate(evaluation.pre_recovery_errors, evaluation.post_recovery_errors)
            if evaluation.pre_recovery_errors is not None else None,
        "correct_claims": sum(c.accuracy == "correct" for c in evaluation.claims),
        "incorrect_claims": sum(c.accuracy == "incorrect" for c in evaluation.claims),
        "unverifiable_claims": sum(c.accuracy == "unverifiable" for c in evaluation.claims),
        "unsupported_claims": sum(c.support == "unsupported" for c in evaluation.claims),
        "detected_errors": len(matched), "missed_errors": len(verified - matched),
        "false_positive_flags": sum(f.matched_error_id is None for f in evaluation.reviewer_flags),
        "missing_components": sum(c.verdict == "missing" for c in components.values()),
        "undefined_policy": "null means zero denominator, incomplete inventory, or not applicable; inspect inventory flags and counts."
    }
    results["incorrect_claim_rate"] = incorrect_claim_rate(
        sum(c.accuracy == "incorrect" for c in evaluation.claims), len(evaluation.claims)
        ) if evaluation.claim_inventory_complete else None
    results["error_detection_f1"] = error_detection_f1(
        results["error_detection_precision"], results["error_detection_recall"])
    results["new_errors_introduced"] = None  # Requires independently aligned pre/post error inventories.
    return results

def incorrect_claim_rate(incorrect, total):
    if incorrect > total:
        raise ValueError("Incorrect claims exceed total factual claims")
    return ratio(incorrect, total)

def error_detection_f1(precision, recall):
    if precision is None or recall is None:
        return None
    if not 0 <= precision <= 1 or not 0 <= recall <= 1:
        raise ValueError("Precision and recall must be within zero and one")
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

def newly_introduced_errors(before_error_ids, after_error_ids):
    return len(set(after_error_ids) - set(before_error_ids))

def quality_improvement(before, after):
    return None if before is None or after is None else after - before
