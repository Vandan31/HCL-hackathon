"""
COMPONENT : ingest (data + ingestion)
PURPOSE   : Every tunable value and fixed mapping for turning hand-collected scheme text into chunks.
INPUTS    : none (constants imported by src/ingest/convert_txt.py and src/ingest/build_chunks.py)
OUTPUTS   : folder paths, chunk size limit, myScheme heading -> section map, scheme id map
DEPENDS ON: docs/DATA_FORMAT.md (section names and language codes must match it)
PANEL NOTE: Adding a scheme = paste its myScheme page into docs/schemes/ and add one line to SCHEME_IDS.
"""

# Hand-pasted myScheme pages, one .txt per scheme (D-001: copied by a human, never scraped).
RAW_DIR = "docs/schemes"
# Structured scheme files in the DATA_FORMAT §1 template, one <id>.json per scheme.
SCHEMES_DIR = "data/schemes"
# The ONLY file retrieval reads (DATA_FORMAT §2).
CHUNKS_PATH = "data/processed/chunks.jsonl"

# DEMO-KNOB: a section longer than this (in words, in any language) is split into "#1", "#2", ...
# DATA_FORMAT §2 asks for ~100-300 words per chunk and a split above ~400.
MAX_WORDS = 400

# MOCK: none of the pasted pages included their myScheme URL and agents may not look it up (D-001).
# The team chose this placeholder on 2026-10-27; replace per scheme in data/schemes/<id>.json.
SOURCE_URL_MISSING = "not available"

# Written into every converted scheme file (DATA_FORMAT §1: shows the data is dated and hand-collected).
COLLECTED_ON = "2026-10-27"
COLLECTED_BY = "Jaya"

# Language of the pasted pages. All 26 are the English myScheme view; hi/gu versions can be
# added to the JSON by hand later (leave a language out rather than writing "").
RAW_LANG = "en"

# myScheme page heading (exact line) -> DATA_FORMAT section name. None = not a section: the block
# is dropped. WHY drop FAQs: the pasted FAQ blocks hold questions only, no answers, so they add
# no facts and would make a question look "answered" by a passage that only repeats it.
HEADINGS = {
    "Details": "details",
    "Benefits": "benefits",
    "Eligibility": "eligibility",
    "Exclusions": "exclusions",
    "Application Process": "how_to_apply",
    "Documents Required": "documents",
    "Frequently Asked Questions": None,
    "Sources And References": None,
}

# Page furniture (button labels) that sits in the header, not scheme text.
SKIP_LINES = {"Check Eligibility", "Apply Now"}

# Raw file name (without .txt) -> scheme id. WHY a fixed map instead of auto-slugs: ids become
# scheme_id in every chunk and eval label and must never change (DATA_FORMAT §1), and file
# names like "RightToInformation" don't make good ids. Short, lowercase, joined by "-".
SCHEME_IDS = {
    "Agnipath Yojana": "agnipath",
    "Financial Assistance for Tagore Cultural Complexes": "tagore-cultural-complexes",
    "Financial Assistance to Helpless Artists": "helpless-artists-assistance",
    "Halpati Housing Scheme": "halpati-housing",
    "Indira Gandhi National Disability Pension Scheme": "igndps",
    "Interest Subsidy Scheme on Education Loan": "education-loan-interest-subsidy",
    "Loan For Foreign Study": "foreign-study-loan-sebc",
    "Loan for Small Businesses": "small-business-loan-daadc",
    "MOBC Meritorious Students": "mobc-meritorious-students",
    "Mahila Samruddhi Yojana": "mahila-samruddhi-daadc",
    "MarketDevelopmentAssistance": "market-development-assistance",
    "Meghalaya Motorcaravan Scheme": "meghalaya-motorcaravan",
    "National Savings Time Deposit": "national-savings-time-deposit",
    "NationalPostDoctoralFellowship": "national-post-doctoral-fellowship",
    "One District One Product (ODOP) Awards": "odop-awards",
    "Padma Awards": "padma-awards",
    "Pension Scheme to Widow": "widow-pension-dnhdd",
    "Police Medal for Meritorious Service": "police-medal-meritorious-service",
    "Post Graduate Indira Gandhi Scholarship For Single Girl Child": "pg-scholarship-single-girl-child",
    "Pradhan Mantri Virasat ka Samvardhan": "pm-virasat-ka-samvardhan",
    "Primary Cooperative Agriculture and Rural Development Bank": "pcardb-power-tiller",
    "Rashtriya Krishi Vigyan Puraskar": "rashtriya-krishi-vigyan-puraskar",
    "RightToInformation": "rti-fellowship",
    "Teachers Associateship for Research Excellence": "tare",
    "The Lokpal of India Internship Scheme": "lokpal-internship",
    "Women Scientist Scheme-A": "women-scientist-scheme-a",
}
