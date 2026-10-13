"""Shared V2 discovery rules; dates belong to each run, not configuration."""
from config import COMPANIES, SOURCE_GROUPS, INDUSTRY_QUERIES, EXCLUDED_TITLE_TERMS, EXCLUDED_LINK_TERMS

DIMENSIONS = {
    'products': '("product launch" OR "new flavor" OR "new flavour")',
    'pricing': '(price OR pricing)',
    'retail': '(retail OR distribution)',
    'marketing': '(marketing OR campaign)',
    'business': '(funding OR acquisition OR partnership)',
    'consumers': '("consumer demand" OR sales)',
}
PILOT_SOURCE_GROUP = 'beverage_and_food_trade'
ENTITY_RULE_VERSION = 'v2.1'
BEVERAGE_CONTEXT = r'\b(?:soda|beverages?|drinks?|probiotic|prebiotic|flavou?rs?)\b'
NON_ARTICLE_PATHS = ('/video/', '/videos/', '/photos/', '/podcast/', '/news/events/')