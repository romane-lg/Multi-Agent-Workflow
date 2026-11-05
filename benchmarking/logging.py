"""Non-invasive backend observer with explicit unknown usage and configurable prices."""
from datetime import datetime, timezone
import time

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def count(value):
    return value if type(value) is int and value >= 0 else None

def normalized_usage(usage):
    usage = usage or {}
    def pick(*keys):
        for key in keys:
            if key in usage:
                return count(usage[key])
        return None
    input_tokens = pick("input_tokens", "prompt_tokens")
    output_tokens = pick("output_tokens", "completion_tokens")
    total = pick("total_tokens")
    if total is None and input_tokens is not None and output_tokens is not None:
        total = input_tokens + output_tokens
    cached = pick("cached_input_tokens", "cached_prompt_tokens")
    if cached is None:
        details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
        if isinstance(details, dict):
            cached = count(details.get("cached_tokens"))
    return {"input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": total, "cached_input_tokens": cached,
            "model_calls": pick("successful_requests")}

def api_cost(model, usage, pricing):
    if pricing is None or model not in pricing.models:
        return None
    rates = pricing.models[model]
    ins, outs, cached = (usage[k] for k in ("input_tokens", "output_tokens", "cached_input_tokens"))
    if ins is None or outs is None:
        return None
    if cached is not None and cached > ins:
        raise ValueError("Cached tokens exceed input tokens")
    if rates.cached_input_per_million is not None:
        if cached is None:
            return None
        value = (ins - cached) * rates.input_per_million + cached * rates.cached_input_per_million
    else:
        if cached:  # Do not invent a price for known cache-discounted tokens.
            return None
        value = ins * rates.input_per_million
    return round((value + outs * rates.output_per_million) / 1_000_000, 10)

def aggregate(rows):
    result = {}
    for key in ("input_tokens", "output_tokens", "total_tokens", "model_calls", "tool_calls", "api_cost"):
        values = [r.get(key) for r in rows]
        result[key] = sum(values) if values and all(v is not None for v in values) else None
        result["known_" + key] = sum(v for v in values if v is not None) if values else None
    return result

class ObservedBackend:
    def __init__(self, backend, pricing=None):
        self.backend, self.pricing = backend, pricing
        self.rows = []

    def generate(self, stage, schema, instructions, payload):
        began = time.monotonic()
        row = {"execution_index": len(self.rows) + 1, "agent_name": stage,
               "start_time": utc_now(), "end_time": None, "duration_seconds": None,
               "model": None, "model_version": None, "status": "failed", "input_tokens": None,
               "output_tokens": None, "total_tokens": None, "cached_input_tokens": None,
               "model_calls": None, "tool_calls": None, "api_cost": None,
               "error_type": None, "error_message": None, "pricing_error_type": None,
               "currency": self.pricing.currency if self.pricing else None,
               "pricing_version": self.pricing.pricing_version if self.pricing else None,
               "pricing_effective_date": str(self.pricing.effective_date) if self.pricing and self.pricing.effective_date else None,
               "cost_method": "configured_token_rates_estimate" if self.pricing else None}
        try:
            result = self.backend.generate(stage, schema, instructions, payload)
            usage = normalized_usage(result.usage)
            row.update(usage, model=result.model, model_version=getattr(result, "model_version", None),
                       tool_calls=count(getattr(result, "tool_calls", None)))
            calls = count(getattr(result, "model_calls", None))
            if calls is not None:
                row["model_calls"] = calls
            try:
                row["api_cost"] = api_cost(result.model, usage, self.pricing)
            except (ValueError, TypeError) as exc:
                # Optional accounting must not change an agent's successful result.
                row["pricing_error_type"] = type(exc).__name__
            row["status"] = "completed"
            return result  # Preserve the original result and content exactly.
        except Exception as exc:
            row.update(error_type=type(exc).__name__,
                       error_message="Agent execution failed; exception text omitted to avoid credential exposure.")
            raise
        finally:
            row.update(end_time=utc_now(), duration_seconds=round(time.monotonic() - began, 6))
            self.rows.append(row)
