"""
COMPONENT : tts
PURPOSE   : Turn an answer into text the Gujarati / Hindi voice can actually say: drop [S1] markers, write numbers
            and ₹ as words, and rewrite English terms and acronyms in the language's own script.
INPUTS    : answer text, language code ("gu" | "hi" | "en"; "en" = Latin-letter mode, used for English AND Hinglish)
OUTPUTS   : speakable text (gu/hi: native script; en: Latin letters, numbers as English words)
DEPENDS ON: config/tts.py (word lists); Python standard library only, so it is testable without the models
PANEL NOTE: The AI4Bharat voices only know their own script and silently skip anything else ("PM-KISAN" came out
            as silence in our first test); these plain rules fix that with no extra model.
"""
import re

from config.tts import (EN_NUMBER_WORDS, EN_SYMBOL_WORDS, EN_TENS, EN_WORDS, LATIN_WORDS, LETTER_NAMES,
                        MAX_LATIN_SHARE, NUMBER_WORDS, SCALE_WORDS, SYMBOL_WORDS)

LANGS = ("gu", "hi", "en")


def _symbols(lang):
    return EN_SYMBOL_WORDS if lang == "en" else SYMBOL_WORDS[lang]


def _under_100(n: int, lang: str) -> str:
    """0–99 as words: a lookup table for gu/hi (irregular), tens + ones for English."""
    if lang != "en":
        return NUMBER_WORDS[lang][n]
    if n < 20:
        return EN_NUMBER_WORDS[n]
    tens, ones = divmod(n, 10)
    return EN_TENS[tens] + (f" {EN_NUMBER_WORDS[ones]}" if ones else "")

CITATION = re.compile(r"\s*\[S\d+\]")
# A number like 6,000 / 1,25,000 (Indian grouping) / 2.5, optionally led by ₹.
NUMBER = re.compile(r"(₹\s?)?(\d[\d,]*)(\.\d+)?(\s?%)?")
LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z.]*[A-Za-z]|[A-Za-z]")


def latin_share(text: str) -> float:
    """Fraction of letters that are Latin (a-z). Used to refuse Hinglish/English, which the gu/hi voices can't read."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isascii()) / len(letters)


def is_speakable(text: str) -> bool:
    """True if the text is mostly in the language's own script (see MAX_LATIN_SHARE in config/tts.py)."""
    return latin_share(text) <= MAX_LATIN_SHARE


def number_to_words(n: int, lang: str) -> str:
    """Integer -> words in the Indian system: 1,25,000 -> 'एक लाख पच्चीस हज़ार' / 'one lakh twenty five thousand'."""
    scale = SCALE_WORDS[lang]
    if n < 100:
        return _under_100(n, lang)
    parts = []
    # WHY this order: Indian numbering groups as crore (10^7), lakh (10^5), thousand (10^3), hundred (10^2).
    for size, name in ((10**7, "crore"), (10**5, "lakh"), (10**3, "thousand"), (10**2, "hundred")):
        if n >= size:
            count, n = divmod(n, size)
            # crore can exceed 99 (e.g. 150 crore) -> recurse for the count
            parts.append(f"{number_to_words(count, lang)} {scale[name]}")
    if n:
        parts.append(_under_100(n, lang))
    return " ".join(parts)


def _say_number(match: re.Match, lang: str) -> str:
    rupee, digits, decimal, percent = match.groups()
    whole = int(digits.replace(",", ""))
    spoken = number_to_words(whole, lang)
    sym = _symbols(lang)
    if decimal:
        # "2.5" -> "two point five": digit by digit after the point, as people say it.
        spoken += " " + sym["."] + " " + " ".join(_under_100(int(d), lang) for d in decimal[1:])
    if percent:
        spoken += " " + sym["%"]
    if rupee:
        spoken += " " + sym["₹"]   # ₹6,000 is said "six thousand rupees", so the word goes after
    return spoken


def _say_latin_en(token: str) -> str:
    """English/Hinglish mode: keep words as they are, but make acronyms and web addresses sayable."""
    known = EN_WORDS.get(token.lower())
    if known:
        return known
    # WHY: a short all-capitals word is an acronym ("SC", "OBC", "PMAY"); spaced letters make the voice spell it.
    # 4 letters max: longer capitals are usually names ("KISAN") — add those to EN_WORDS in config/tts.py.
    if token.isupper() and 1 < len(token) <= 4 and "." not in token:
        return " ".join(token)
    if "." in token:
        return " dot ".join(token.split("."))   # e.g. "pmkisan.gov.in" -> "pmkisan dot gov dot in"
    return token


def _say_latin(match: re.Match, lang: str) -> str:
    token = match.group(0)
    if lang == "en":
        return _say_latin_en(token)
    known = LATIN_WORDS[lang].get(token.lower())
    if known:
        return known
    # FALLBACK: unknown English word or acronym -> spell it letter by letter rather than skip it silently.
    return " ".join(LETTER_NAMES[lang][c] for c in token.lower() if c in LETTER_NAMES[lang])


def normalize(text: str, lang: str) -> str:
    """Make an answer speakable by the AI4Bharat voice for `lang` ("gu", "hi", or "en" for English/Hinglish)."""
    if lang not in LANGS:
        raise ValueError(f"unsupported language: {lang}")
    text = CITATION.sub("", text)
    text = text.replace("।", ".").replace("॥", ".")   # WHY: the Hindi model's vocabulary has no danda; '.' still makes a pause
    text = NUMBER.sub(lambda m: _say_number(m, lang), text)
    text = LATIN_TOKEN.sub(lambda m: _say_latin(m, lang), text)
    text = re.sub(r"(?<=\S)-(?=\S)", " ", text)          # "PM-KISAN" -> two spoken words, not a minus sign
    for sym in ("&", "+", "/", "%", "₹"):
        text = text.replace(sym, f" {_symbols(lang)[sym]} ")
    return re.sub(r"\s+", " ", text).strip()
