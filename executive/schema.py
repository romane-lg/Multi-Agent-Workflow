from typing import Literal

from pydantic import Field

from researcher.schema import StrictModel


Focus = Literal["ontario_retail", "pricing", "product_launch", "marketing", "bc_expansion"]
TITLES = {
    "ontario_retail": "Ontario retail", "pricing": "Pricing & margins",
    "product_launch": "Product pipeline", "marketing": "Marketing & demand",
    "bc_expansion": "BC expansion",
}


class MarketSignal(StrictModel):
    text: str = Field(description="At most 40 words: qualitative competitive signal with attribution, scope and limitation. No digits, metrics or dates; source dates are rendered separately.")
    insight_ids: list[str]


class TopicCard(StrictModel):
    implication: str = Field(description="At most 25 words: why this matters to Fizzera.")
    action: str = Field(description="At most 25 words: concrete next action already supported by the Analyst recommendation, phrased as a proposal.")
    metric_or_gate: str = Field(description="At most 20 words: existing success measure or evidence needed before deciding. No invented KPI, date or budget.")
    caveat: str = Field(description="At most 25 words: material uncertainty or unresolved review issue. Plain language.")


class TopicBuckets(StrictModel):
    ontario_retail: TopicCard
    pricing: TopicCard
    product_launch: TopicCard
    marketing: TopicCard
    bc_expansion: TopicCard


class ExecutiveBrief(StrictModel):
    strategic_outlook: str = Field(description="Target 45-60 words, maximum 80: answer Fizzera's strategic outlook directly, separating directional lessons from evidence of success.")
    priority_focuses: list[Focus] = Field(description="Exactly three different topics in order of executive attention; preserve Ontario-first priorities.")
    market_signals: list[MarketSignal] = Field(description="Two or three useful signals from this historical sample, with original source limitations.")
    topics: TopicBuckets
