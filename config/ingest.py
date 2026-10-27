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

# MOCK: none of the pasted pages included their own myScheme URL and agents may not look it up (D-001).
# The team chose the myScheme search page as a stand-in link (2026-10-27, D-008); replace it per scheme
# in data/schemes/<id>.json with the real page URL (the converter keeps a URL once it is set).
SOURCE_URL_MISSING = "https://www.myscheme.gov.in/search"

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

# Operators a criterion may use. Must match OPS in src/eligibility/rules.py (Vaidehi's engine);
# every rule of a scheme must be met (AND), there is no OR.
CRITERIA_OPS = {"eq", "neq", "gte", "lte", "gt", "lt", "in", "not_in"}

# Shared answer vocabulary for "criteria" (PLAN §4.4): field -> "number", "bool", or the allowed
# lowercase string values. WHY one list: the checklist asks each field once and reuses the answer
# across schemes, so "state" must mean the same thing in every scheme file.
# (Q) = already has a follow-up question in config/eligibility.py; others show "verify at office"
# until Vaidehi adds a question for them.
CRITERIA_FIELDS = {
    # Person
    "age": "number",                                                     # (Q) years
    "gender": ["female", "male", "other"],                               # (Q)
    "occupation": ["farmer", "labourer", "self_employed", "salaried", "student", "other"],  # (Q)
    "marital_status": ["widow", "married", "unmarried", "divorced"],
    "citizen_of_india": "bool",
    "resident_of_india": "bool",
    "state": ["gujarat", "assam", "meghalaya", "tamil nadu", "dadra and nagar haveli and daman and diu", "other"],
    "district": ["surat", "tapi", "valsad", "navsari", "narmada", "bharuch", "chhotaudepur", "vadodara", "other"],
    "rural_resident": "bool",
    "social_category": ["sc", "st", "obc", "sebc", "mobc", "general"],
    "halpati_community": "bool",
    "minority_or_ews": "bool",
    "is_disabled": "bool",
    "disability_percent": "number",
    # Money (rupees per year)
    "annual_family_income": "number",
    "annual_income": "number",                                           # applicant's own income
    "bpl_household": "bool",
    "aay_family": "bool",
    "aay_or_economically_backward": "bool",
    "poor_economic_condition": "bool",
    "credit_defaulter": "bool",
    # Family / job exclusions
    "govt_employee": "bool",            # (Q) anyone in the family serving or retired govt employee
    "serving_govt_employee": "bool",    # the applicant personally, serving now
    "psu_employee": "bool",
    "political_office": "bool",
    "class1_contractor": "bool",
    "govt_consultant": "bool",
    # Education
    "education_level": ["undergraduate", "postgraduate"],
    "field_of_study": ["law", "political science", "public administration", "public policy",
                       "management", "economics", "human rights", "other"],
    "class12_percent": "number",
    "hsc_percentile": "number",
    "degree_aggregate_percent": "number",
    "ug_years_completed": "number",
    "first_year_regular_pg": "bool",
    "professional_course": "bool",
    "distance_education": "bool",
    "only_girl_child": "bool",
    "meets_mobc_merit_marks": "bool",
    "has_own_laptop": "bool",
    "has_education_loan": "bool",
    "studying_abroad": "bool",
    "course_duration_years": "number",
    "applied_within_6_months_abroad": "bool",
    "has_solvent_guarantor": "bool",
    # Work / business
    "plans_own_business": "bool",
    "can_provide_two_guarantors": "bool",
    "has_driving_licence": "bool",
    "tourism_experience_years": "number",
    "loan_for_power_tiller": "bool",
    "artist_with_contribution": "bool",
    # Research / professional
    "has_phd_or_thesis_submitted": "bool",
    "has_phd_science_or_ms_md": "bool",
    "has_science_pg_or_phd": "bool",
    "availed_npdf_before": "bool",
    "regular_position_state_or_private": "bool",
    "has_ongoing_project_or_fellowship": "bool",
    "holds_permanent_position": "bool",
    "agri_scientist_public_institution": "bool",
    "rti_field_professional": "bool",
    "rti_experience": "bool",
    "proven_credentials": "bool",
    "research_aptitude": "bool",
    "distinguished_service": "bool",
    "clean_service_record": "bool",
    "serving_police_or_capf": "bool",
    "years_of_service": "number",
    "meets_acr_requirements": "bool",
    "shape_1_fitness": "bool",
    "meets_forces_standards": "bool",
    "receives_other_widow_pension": "bool",
    # Organisations
    "applicant_type": ["individual", "organisation", "state_ut", "district", "indian_mission",
                       "ecommerce_platform", "central_ministry"],
    "registered_3_years": "bool",
    "cultural_work_3_years": "bool",
    "can_fund_matching_share": "bool",
    "recommended_by_govt_agency": "bool",
    "gobardhan_registered_plant": "bool",
    "markets_fom_lfom_prom": "bool",
    "meets_fco_specs": "bool",
}

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
