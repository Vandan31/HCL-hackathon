"""
COMPONENT : lang (language detection)
PURPOSE   : Every tunable value for language detection, in one place so it can be changed live.
INPUTS    : none (constants imported by src/lang/detect.py)
OUTPUTS   : script ranges, IndicLID model paths + guards, Whisper hint threshold, Hinglish word list
DEPENDS ON: nothing
PANEL NOTE: Layered detection: free script rules first, the IndicLID model only for the hard cases
            (Devanagari languages, Indian languages typed in Roman letters), Whisper's guess for speech.
"""

# Unicode block ranges per script (ISO 15924 codes). WHY: every Indic script has its own block,
# so the script of a character narrows the language down with no model at all.
SCRIPT_RANGES = {
    "Deva": (0x0900, 0x097F),   # Devanagari: Hindi, Marathi, Nepali, Maithili, ... -> ask IndicLID
    "Beng": (0x0980, 0x09FF),   # Bengali-Assamese: Bengali or Assamese -> ask IndicLID
    "Guru": (0x0A00, 0x0A7F),   # Gurmukhi: Punjabi
    "Gujr": (0x0A80, 0x0AFF),   # Gujarati
    "Orya": (0x0B00, 0x0B7F),   # Odia
    "Taml": (0x0B80, 0x0BFF),   # Tamil
    "Telu": (0x0C00, 0x0C7F),   # Telugu
    "Knda": (0x0C80, 0x0CFF),   # Kannada
    "Mlym": (0x0D00, 0x0D7F),   # Malayalam
    "Arab": (0x0600, 0x06FF),   # Perso-Arabic: Urdu, Kashmiri, Sindhi -> ask IndicLID
}

# Language each script means when we can't (or don't) ask the model. Scripts used by one language
# only are final; the shared ones (Deva, Beng, Arab, Latn) give the most common language.
# DEMO-KNOB: the 3rd demo language is whatever the documents cover; detection itself covers all.
SCRIPT_TO_LANG = {
    "Deva": "hi", "Beng": "bn", "Guru": "pa", "Gujr": "gu", "Orya": "or", "Taml": "ta",
    "Telu": "te", "Knda": "kn", "Mlym": "ml", "Arab": "ur", "Latn": "en",
}

# Scripts shared by several languages: only for these do we run IndicLID.
# WHY: for Gujarati/Tamil/... script the answer is already certain; a model can only add errors.
AMBIGUOUS_SCRIPTS = {"Deva", "Beng", "Arab", "Latn"}

# Languages our documents + answer templates cover. Output field "supported" tells the answer
# engine whether it has native refusal templates / documents for the detected language.
# DEMO-KNOB: add "mr" etc. here once documents in that language are ingested.
DOC_LANGS = {"en", "hi", "gu"}

# DEMO-KNOB: language used when the text has no letters at all (e.g. "123" or "").
DEFAULT_LANG = "en"

# DEMO-KNOB: highest confidence for "English" when only the rules decided it (no Hinglish words,
# IndicLID off or skipped). WHY: Roman letters can be any Indian language ("kem cho" is Gujarati),
# so a rules-only English call is a default, not a certainty.
LATIN_DEFAULT_CONF = 0.5

# ---------------------------------------------------------------- IndicLID (AI4Bharat) model
# DEMO-KNOB: False = script rules + Hinglish list only (the original detector, no model files).
USE_LID = True

# fastText models from github.com/AI4Bharat/IndicLID releases v1.0 (MIT licence), not in git
# (~540 MB). Download indiclid-ftn.zip + indiclid-ftr.zip from that release and unzip into
# models/indiclid/. FTN = native scripts, FTR = Roman script.
LID_NATIVE_MODEL = "models/indiclid/indiclid-ftn/model_baseline_roman.bin"
LID_ROMAN_MODEL = "models/indiclid/indiclid-ftr/model_baseline_roman.bin"

# DEMO-KNOB: minimum model probability before it may override the script rules.
# 0.5 measured on our probes: romanised Gujarati scored 0.53, wrong guesses mostly >= 0.68, so this
# alone isn't enough: LID_MIN_WORDS and LID_ACCEPT below do the real filtering.
LID_MIN_CONF = 0.5

# DEMO-KNOB: below this many words the model is ignored. WHY: measured, "apply online" was
# classified as romanised Gujarati (0.68); 2-word queries don't carry enough signal.
LID_MIN_WORDS = 3

# Languages the model's answer is accepted for. WHY: measured, IndicLID labels Hinglish as Maithili
# (0.77-0.92) and "PM किसान का पैसा कब आएगा?" as Kashmiri (1.00): close relatives of Hindi it
# confuses on short queries. Labels outside this set are ignored and the rules decide.
# PANEL: Why not trust the model fully? -> on 25 short citizen queries the rule fallback is safer;
#        we accept the model only for major languages where we measured it right.
LID_ACCEPT = {"en", "hi", "gu", "mr", "bn", "as", "pa", "or", "ta", "te", "kn", "ml", "ur", "ne"}

# IndicLID's 3-letter labels -> the 2-letter ISO 639-1 codes the rest of the app (and Whisper) uses.
LID_TO_ISO = {
    "asm": "as", "ben": "bn", "brx": "brx", "doi": "doi", "eng": "en", "guj": "gu", "hin": "hi",
    "kan": "kn", "kas": "ks", "kok": "kok", "mai": "mai", "mal": "ml", "mni": "mni", "mar": "mr",
    "nep": "ne", "ori": "or", "pan": "pa", "san": "sa", "sat": "sat", "snd": "sd", "tam": "ta",
    "tel": "te", "urd": "ur",
}

# ---------------------------------------------------------------- Speech (faster-whisper hint)
# DEMO-KNOB: Whisper's language probability needed before it can overrule the text detector.
# WHY a high bar: Whisper is known to confuse Hindi/Urdu on short clips (Hypothesized for our
# clips, not measured yet); the transcript's script is usually the stronger evidence.
WHISPER_MIN_PROB = 0.8

# ---------------------------------------------------------------- Hinglish (rules)
# DEMO-KNOB: share of Latin-script words that must be Hindi function words to call it Hinglish.
# Raise it -> fewer English questions misread as Hinglish; lower it -> catches lighter Hinglish.
HINGLISH_MIN_RATIO = 0.25

# DEMO-KNOB: share of Latin letters inside Devanagari/Gujarati text to flag it as code-mixed
# (e.g. "PM किसान का पैसा कब आएगा" has a little Latin: still plain Hindi below this share).
MIXED_SCRIPT_MIN_RATIO = 0.30

# Romanised Hindi words that are (almost) never English words. WHY: function words and common
# verbs identify Hinglish reliably. We deliberately leave out scheme names ("kisan", "yojana",
# "awas") because English questions use them too ("PM Kisan eligibility" is English).
# PANEL: Why keep a word list next to IndicLID? -> measured, IndicLID calls Hinglish "Maithili";
#        the list catches it first, for free.
HINGLISH_WORDS = {
    "hai", "hain", "kya", "kaise", "kaisa", "kaun", "kaunsa", "kaunse", "kab", "kahan", "kitna",
    "kitne", "kyun", "mujhe", "mera", "meri", "mere", "hum", "humein", "aap", "aapko", "tum",
    "chahiye", "milega", "milegi", "milta", "milti", "mil", "sakta", "sakti", "sakte", "karna",
    "karein", "kare", "karu", "karo", "liye", "nahi", "nahin", "bhi", "aur", "ya", "ka", "ki",
    "ke", "ko", "se", "mein", "par", "wala", "wali", "wale", "paisa", "paise", "kitni", "batao",
    "bataye", "bataiye", "kripya", "sarkari", "kaha", "hoga", "hogi", "tha", "thi",
    "banaye", "banwaye", "banega", "banegi", "banta", "banti", "banana", "banwana", "lena", "dena",
}

# DEMO-KNOB: minimum number of Hindi words before we call text Hinglish.
# WHY: protects very short English queries (one stray match in 2 words would be 50%).
HINGLISH_MIN_WORDS = 2

# English function words, checked after Hinglish and before IndicLID. WHY: measured, IndicLID's roman
# model labelled "How do I renew my passport?" as Bengali (0.56); a sentence full of "how/do/my" is English.
# Scheme words (loan, card, pension) are left out: Hinglish and romanised Gujarati questions use them too.
ENGLISH_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "do", "does", "did", "i", "my", "you", "your",
    "how", "what", "when", "where", "which", "who", "why", "can", "could", "should", "will", "would",
    "for", "of", "to", "in", "on", "at", "with", "and", "or", "not", "this", "that", "it", "there",
    "from", "by", "am", "have", "has", "get", "need", "much", "many", "any", "if", "under",
}

# DEMO-KNOB: English words needed (count and share of Latin words) to call Roman text English
# without asking the model.
ENGLISH_MIN_WORDS = 2
ENGLISH_MIN_RATIO = 0.3
