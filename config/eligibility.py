"""
COMPONENT : eligibility (config)
PURPOSE   : Every value the eligibility checklist may need to change live, plus the wording of each follow-up question.
INPUTS    : none
OUTPUTS   : constants imported by src/eligibility/rules.py
DEPENDS ON: nothing
PANEL NOTE: Question wording lives here, not in code, so a translation fix during the demo is a one-line edit.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCHEMES_DIR = ROOT / "data" / "schemes"   # DEMO-KNOB: where Jaya's verified scheme JSONs live (PLAN §4.4)
USE_MOCK_SCHEMES = True                    # DEMO-KNOB: fall back to src/eligibility/mock_schemes.json for schemes not in SCHEMES_DIR yet
MOCK_SCHEMES_FILE = ROOT / "src" / "eligibility" / "mock_schemes.json"

MAX_QUESTIONS = 5          # DEMO-KNOB: stop asking after this many answers; the rest stay "unknown" (verify at office)
STOP_ON_FIRST_FAIL = True  # DEMO-KNOB: once one rule is clearly not met, stop asking more questions
DEFAULT_LANG = "en"        # DEMO-KNOB: language used when a question has no translation for the requested one

# WHY: a fixed yes/no option list, so every yes/no answer arrives as a real boolean, not "Yes"/"हाँ"/"હા" text.
YES_NO = [
    {"value": True,  "label": {"en": "Yes", "hi": "हाँ", "gu": "હા"}},
    {"value": False, "label": {"en": "No",  "hi": "नहीं", "gu": "ના"}},
]

# DEMO-KNOB: one entry per field used in any scheme's "criteria". An empty options list means "type a number".
# A field missing here is never asked; its rules stay "unknown" so the user is told to verify at the office.
FIELD_QUESTIONS = {
    "occupation": {
        "text": {"en": "What is your main work?",
                 "hi": "आपका मुख्य काम क्या है?",
                 "gu": "તમારો મુખ્ય વ્યવસાય શું છે?"},
        "options": [
            {"value": "farmer",        "label": {"en": "Farmer", "hi": "किसान", "gu": "ખેડૂત"}},
            {"value": "labourer",      "label": {"en": "Labourer", "hi": "मज़दूर", "gu": "મજૂર"}},
            {"value": "self_employed", "label": {"en": "Self-employed", "hi": "स्वरोज़गार", "gu": "સ્વરોજગાર"}},
            {"value": "salaried",      "label": {"en": "Salaried job", "hi": "नौकरी (वेतन)", "gu": "નોકરી (પગાર)"}},
            {"value": "student",       "label": {"en": "Student", "hi": "विद्यार्थी", "gu": "વિદ્યાર્થી"}},
            {"value": "other",         "label": {"en": "Other", "hi": "अन्य", "gu": "અન્ય"}},
        ],
    },
    "land_owner": {
        "text": {"en": "Does your family own farm land in its name?",
                 "hi": "क्या आपके परिवार के नाम पर खेती की ज़मीन है?",
                 "gu": "શું તમારા પરિવારના નામે ખેતીની જમીન છે?"},
        "options": YES_NO,
    },
    "income_tax_payer": {
        "text": {"en": "Did anyone in your family pay income tax last year?",
                 "hi": "क्या पिछले साल आपके परिवार में किसी ने आयकर भरा था?",
                 "gu": "શું ગયા વર્ષે તમારા પરિવારમાં કોઈએ આવકવેરો ભર્યો હતો?"},
        "options": YES_NO,
    },
    "govt_employee": {
        "text": {"en": "Is anyone in your family a serving or retired government employee?",
                 "hi": "क्या आपके परिवार में कोई सरकारी कर्मचारी या रिटायर्ड सरकारी कर्मचारी है?",
                 "gu": "શું તમારા પરિવારમાં કોઈ સરકારી કર્મચારી અથવા નિવૃત્ત સરકારી કર્મચારી છે?"},
        "options": YES_NO,
    },
    "age": {
        "text": {"en": "How old are you (in years)?",
                 "hi": "आपकी उम्र कितनी है (साल में)?",
                 "gu": "તમારી ઉંમર કેટલી છે (વર્ષમાં)?"},
        "options": [],
    },
    "has_bank_account": {
        "text": {"en": "Do you have a savings account in a bank or post office?",
                 "hi": "क्या आपका बैंक या डाकघर में बचत खाता है?",
                 "gu": "શું તમારું બેંક અથવા પોસ્ટ ઓફિસમાં બચત ખાતું છે?"},
        "options": YES_NO,
    },
    "gender": {
        "text": {"en": "What is your gender?",
                 "hi": "आपका लिंग क्या है?",
                 "gu": "તમારું લિંગ શું છે?"},
        "options": [
            {"value": "female", "label": {"en": "Female", "hi": "महिला", "gu": "સ્ત્રી"}},
            {"value": "male",   "label": {"en": "Male", "hi": "पुरुष", "gu": "પુરુષ"}},
            {"value": "other",  "label": {"en": "Other", "hi": "अन्य", "gu": "અન્ય"}},
        ],
    },
    "lpg_connection_at_home": {
        "text": {"en": "Does your household already have an LPG gas connection?",
                 "hi": "क्या आपके घर में पहले से LPG गैस कनेक्शन है?",
                 "gu": "શું તમારા ઘરમાં પહેલેથી LPG ગેસ કનેક્શન છે?"},
        "options": YES_NO,
    },
}
