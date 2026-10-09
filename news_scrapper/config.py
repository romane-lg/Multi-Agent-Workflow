COMPANIES = [
    "Olipop",
    "Poppi",
    "Culture Pop",
    "Zevia",
]

COMPANY_ALIASES = {
    "Olipop": ["olipop"],
    "Poppi": ["poppi"],
    "Culture Pop": ["culture pop", "culture-pop"],
    "Zevia": ["zevia"],
}

CATEGORY_KEYWORDS = {
    "products": ["new product", "new flavor", "launch"],
    "pricing": ["price", "pricing"],
    "retail": ["retail", "expansion", "Walmart"],
    "marketing": ["marketing", "campaign"],
    "business": ["funding", "partnership", "acquisition"],
    "consumers": ["consumers", "sales"],
}

INDUSTRY_QUERIES = [
    "prebiotic soda",
    "functional soda",
    "health soda",
    "non alcoholic soda",
]

SOURCE_GROUPS = [
    {
        "name": "beverage_and_food_trade",
        "domains": [
            "bevnet.com",
            "foodbev.com",
            "foodnavigator-usa.com",
            "beverageindustry.com",
        ],
    },
    {
        "name": "retail_and_marketing_trade",
        "domains": [
            "fooddive.com",
            "grocerydive.com",
            "retaildive.com",
            "marketingdive.com",
            "modernretail.co",
            "adage.com",
            "retailbrew.com",
            "marketingbrew.com",
        ],
    },
    {
        "name": "business_and_financial",
        "domains": [
            "reuters.com",
            "bloomberg.com",
            "cnbc.com",
            "forbes.com",
            "wsj.com",
            "morningbrew.com",
        ],
    },
    {
        "name": "company_announcements",
        "domains": [
            "businesswire.com",
            "prnewswire.com",
            "globenewswire.com",
        ],
    },
]

EXCLUDED_TITLE_TERMS = [
    "review",
    "taste test",
    "we tried",
    "coupon",
    "discount code",
    "where to buy",
    "amazon deal",
    "best sodas",
    "ranked",
    "archives",
    "press release wire",
]

EXCLUDED_LINK_TERMS = [
    "/reviews/",
    "/brands/",
    "/category/",
    "/bestof/",
    "/magazine/issue/",
    "/pr/nonalcoholic-beverages/",
]

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
SERPAPI_ENGINE = "google_news"
RESULTS_PER_QUERY = 10
OUTPUT_PATH = "news_scrapper/news_dataset.json"
