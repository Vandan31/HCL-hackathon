"""
COMPONENT : lang (language detection)
PURPOSE   : Every tunable value for language detection, in one place so it can be changed live.
INPUTS    : none (constants imported by src/lang/detect.py)
OUTPUTS   : thresholds, script → language map, Hinglish word list
DEPENDS ON: nothing
PANEL NOTE: Language detection is pure rules, not AI: free, instant and predictable.
"""

# Unicode block ranges per script. WHY: every Indic script has its own block, so the script
# of a character tells us the language family with no model at all.
# To add a language (e.g. Bengali 0x0980-0x09FF -> "bn"), add one row here and one in SCRIPT_TO_LANG.
SCRIPT_RANGES = {
    "Deva": (0x0900, 0x097F),   # Devanagari: Hindi (also Marathi/Nepali, but we only support Hindi)
    "Gujr": (0x0A80, 0x0AFF),   # Gujarati
}

# DEMO-KNOB: which language each script means. Change "Gujr" if the 3rd language changes.
SCRIPT_TO_LANG = {
    "Deva": "hi",
    "Gujr": "gu",
    "Latn": "en",
}

# DEMO-KNOB: language used when the text has no letters at all (e.g. "123" or "").
DEFAULT_LANG = "en"

# DEMO-KNOB: share of Latin-script words that must be Hindi function words to call it Hinglish.
# Raise it -> fewer English questions misread as Hinglish; lower it -> catches lighter Hinglish.
HINGLISH_MIN_RATIO = 0.25

# DEMO-KNOB: share of Latin letters inside Devanagari/Gujarati text to flag it as code-mixed
# (e.g. "PM किसान का पैसा कब आएगा" has a little Latin: still plain Hindi below this share).
MIXED_SCRIPT_MIN_RATIO = 0.30

# Romanised Hindi words that are (almost) never English words. WHY: function words and common
# verbs identify Hinglish reliably. We deliberately leave out scheme names ("kisan", "yojana",
# "awas") because English questions use them too ("PM Kisan eligibility" is English).
# PANEL: Why a word list and not a model? -> 25 schemes, 3 languages: a list is testable and
# explainable; a classifier needs labelled Hinglish data we don't have.
HINGLISH_WORDS = {
    "hai", "hain", "kya", "kaise", "kaisa", "kaun", "kaunsa", "kaunse", "kab", "kahan", "kitna",
    "kitne", "kyun", "mujhe", "mera", "meri", "mere", "hum", "humein", "aap", "aapko", "tum",
    "chahiye", "milega", "milegi", "milta", "milti", "mil", "sakta", "sakti", "sakte", "karna",
    "karein", "kare", "karu", "karo", "liye", "nahi", "nahin", "bhi", "aur", "ya", "ka", "ki",
    "ke", "ko", "se", "mein", "par", "wala", "wali", "wale", "paisa", "paise", "kitni", "batao",
    "bataye", "bataiye", "kripya", "sarkari", "kaha", "hoga", "hogi", "tha", "thi",
}

# DEMO-KNOB: minimum number of Hindi words before we call text Hinglish.
# WHY: protects very short English queries (one stray match in 2 words would be 50%).
HINGLISH_MIN_WORDS = 2
