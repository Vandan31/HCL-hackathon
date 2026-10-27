"""
COMPONENT : tts (config)
PURPOSE   : Every value the speech-output service may need to change live, plus the word lists that turn
            English terms and letters into Gujarati / Hindi script so the voice can say them.
INPUTS    : none
OUTPUTS   : constants imported by src/tts/*.py
DEPENDS ON: nothing
PANEL NOTE: AI4Bharat IndicTTS (FastPitch + HiFi-GAN) speaks the answers; every knob for it is in this one file.
"""
from pathlib import Path

# --- Where the models live (outside the repo: ~1.5 GB per language, never committed) -------------
CHECKPOINT_DIR = Path.home() / "indic-tts" / "checkpoints"   # DEMO-KNOB: folder holding gu/, hi/ from the AI4Bharat release
CACHE_DIR = Path.home() / "indic-tts" / "cache"              # DEMO-KNOB: spoken answers saved here, reused instantly next time

# --- Service ---------------------------------------------------------------------------------------
HOST = "127.0.0.1"
PORT = 5600                       # DEMO-KNOB: the UI dev server uses 5500, so the voice service sits next to it
ALLOWED_ORIGINS = ["http://127.0.0.1:5500", "http://localhost:5500"]   # DEMO-KNOB: pages allowed to call the service
LANGS = ["gu", "hi", "en"]        # DEMO-KNOB: languages to load at start (each model ~3 s to load, ~1.7 GB RAM, estimated)
# Which AI4Bharat checkpoint folder speaks each language. "en+hi" is their code-mixed model: it reads English and
# Hinglish written in Latin letters, so it serves both.
MODEL_FOR_LANG = {"gu": "gu", "hi": "hi", "en": "en+hi"}
LATIN_MODEL = "en+hi"             # WHY: any answer mostly in Latin letters (English, Hinglish) is routed to this model
# DEMO-KNOB: the en+hi model has four voices (female, male, hindifemale, hindimale). Hinglish sounds more natural in
# the Hindi-accented ones, so a Hinglish request for "female" uses "hindifemale". English keeps female/male.
HINGLISH_VOICE = {"female": "hindifemale", "male": "hindimale"}
DEFAULT_SPEAKER = "female"        # DEMO-KNOB: "female" or "male" (the two voices in each AI4Bharat model)
MAX_CHARS = 1200                  # DEMO-KNOB: longer text is refused (a typical answer is 150–400 characters)
MEMORY_CACHE_ITEMS = 200          # DEMO-KNOB: how many recent answers to keep as audio in memory
WARM_UP = True                    # DEMO-KNOB: speak one dummy sentence at start; the first real call is otherwise ~2x slower
# WHY: the gu/hi models only know their own script. Text with more than this share of Latin letters (Hinglish,
# English) is sent to the en+hi model instead; if that model isn't loaded, it's refused and the UI uses the browser voice.
MAX_LATIN_SHARE = 0.5             # DEMO-KNOB

# --- Words the voice must say in the user's language ------------------------------------------------
# DEMO-KNOB: English terms that appear in scheme answers, written the way they should be SPOKEN.
# Keys are matched case-insensitively as whole words. Add a line here when a demo answer mispronounces a name.
LATIN_WORDS = {
    "gu": {
        "pm": "પીએમ", "kisan": "કિસાન", "awas": "આવાસ", "yojana": "યોજના", "aadhaar": "આધાર", "csc": "સીએસસી",
        "lpg": "એલપીજી", "bpl": "બીપીએલ", "ai": "એઆઈ", "mock": "મોક", "myscheme.gov.in": "માય સ્કીમ ડોટ જીઓવી ડોટ ઇન",
        "ujjwala": "ઉજ્જ્વલા", "atal": "અટલ", "pension": "પેન્શન", "mudra": "મુદ્રા", "bank": "બેંક",
    },
    "hi": {
        "pm": "पीएम", "kisan": "किसान", "awas": "आवास", "yojana": "योजना", "aadhaar": "आधार", "csc": "सीएससी",
        "lpg": "एलपीजी", "bpl": "बीपीएल", "ai": "एआई", "mock": "मॉक", "myscheme.gov.in": "माय स्कीम डॉट जीओवी डॉट इन",
        "ujjwala": "उज्ज्वला", "atal": "अटल", "pension": "पेंशन", "mudra": "मुद्रा", "bank": "बैंक",
    },
}

# Letter names, used to spell out unknown English words and acronyms (e.g. "SC" -> "એસ સી").
LETTER_NAMES = {
    "gu": dict(zip("abcdefghijklmnopqrstuvwxyz", [
        "એ", "બી", "સી", "ડી", "ઈ", "એફ", "જી", "એચ", "આઈ", "જે", "કે", "એલ", "એમ", "એન", "ઓ", "પી", "ક્યૂ", "આર",
        "એસ", "ટી", "યુ", "વી", "ડબલ્યુ", "એક્સ", "વાય", "ઝેડ"])),
    "hi": dict(zip("abcdefghijklmnopqrstuvwxyz", [
        "ए", "बी", "सी", "डी", "ई", "एफ़", "जी", "एच", "आई", "जे", "के", "एल", "एम", "एन", "ओ", "पी", "क्यू", "आर",
        "एस", "टी", "यू", "वी", "डब्ल्यू", "एक्स", "वाई", "ज़ेड"])),
}

# Symbols spoken as words.
SYMBOL_WORDS = {
    "gu": {"₹": "રૂપિયા", "%": "ટકા", "&": "અને", "+": "વત્તા", "/": " ", ".": "દશાંશ"},
    "hi": {"₹": "रुपये", "%": "प्रतिशत", "&": "और", "+": "धन", "/": " ", ".": "दशमलव"},
}

# Numbers 1–99 (irregular in both languages, so a table), then the Indian scale words.
# PANEL: Why not a library? -> num2words supports neither Gujarati nor Hindi (checked: CONVERTER_CLASSES).
# TODO(post-hackathon): have a native speaker review these two lists once more.
NUMBER_WORDS = {
    "gu": ("શૂન્ય એક બે ત્રણ ચાર પાંચ છ સાત આઠ નવ દસ અગિયાર બાર તેર ચૌદ પંદર સોળ સત્તર અઢાર ઓગણીસ વીસ "
           "એકવીસ બાવીસ ત્રેવીસ ચોવીસ પચ્ચીસ છવ્વીસ સત્તાવીસ અઠ્ઠાવીસ ઓગણત્રીસ ત્રીસ એકત્રીસ બત્રીસ તેત્રીસ ચોત્રીસ "
           "પાંત્રીસ છત્રીસ સાડત્રીસ આડત્રીસ ઓગણચાલીસ ચાલીસ એકતાલીસ બેતાલીસ તેતાલીસ ચુંમાલીસ પિસ્તાલીસ છેતાલીસ "
           "સુડતાલીસ અડતાલીસ ઓગણપચાસ પચાસ એકાવન બાવન ત્રેપન ચોપન પંચાવન છપ્પન સત્તાવન અઠ્ઠાવન ઓગણસાઠ સાઠ "
           "એકસઠ બાસઠ ત્રેસઠ ચોસઠ પાંસઠ છાસઠ સડસઠ અડસઠ ઓગણસિત્તેર સિત્તેર એકોતેર બોતેર તોતેર ચુમોતેર પંચોતેર "
           "છોતેર સિત્યોતેર ઇઠ્યોતેર ઓગણએંસી એંસી એક્યાસી બ્યાસી ત્યાસી ચોર્યાસી પંચાસી છ્યાસી સિત્યાસી ઇઠ્યાસી "
           "નેવ્યાસી નેવું એકાણું બાણું ત્રાણું ચોરાણું પંચાણું છન્નું સત્તાણું અઠ્ઠાણું નવ્વાણું").split(),
    "hi": ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
           "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस "
           "छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस "
           "उनचास पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ "
           "पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर "
           "उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे "
           "तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split(),
}

# --- English / Hinglish (Latin letters, spoken by the en+hi model) -----------------------------------------
# DEMO-KNOB: terms to say a particular way. Acronyms are spaced out so the voice says the letters, not a word.
EN_WORDS = {
    "pm": "P M", "csc": "C S C", "lpg": "L P G", "bpl": "B P L", "sc": "S C", "st": "S T", "obc": "O B C",
    "myscheme.gov.in": "my scheme dot gov dot in", "ai": "A I", "kisan": "Kisan", "pmjay": "P M J A Y",
}
EN_NUMBER_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                   "sixteen seventeen eighteen nineteen").split()
EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
EN_SYMBOL_WORDS = {"₹": "rupees", "%": "percent", "&": "and", "+": "plus", "/": " ", ".": "point"}

SCALE_WORDS = {   # hundred, thousand, lakh, crore
    "gu": {"hundred": "સો", "thousand": "હજાર", "lakh": "લાખ", "crore": "કરોડ"},
    "hi": {"hundred": "सौ", "thousand": "हज़ार", "lakh": "लाख", "crore": "करोड़"},
    "en": {"hundred": "hundred", "thousand": "thousand", "lakh": "lakh", "crore": "crore"},   # Indian system, as people say it
}
