"""
COMPONENT : tts
PURPOSE   : Turn an answer into text the Gujarati / Hindi voice can actually say: drop [S1] markers, write numbers
            and ₹ as words, and rewrite English terms and acronyms in the language's own script.
INPUTS    : answer text, language code ("gu" | "hi")
OUTPUTS   : speakable text (same language, native script)
DEPENDS ON: config/tts.py (word lists); Python standard library only, so it is testable without the models
PANEL NOTE: The AI4Bharat voices only know their own script and silently skip anything else ("PM-KISAN" came out
            as silence in our first test); these plain rules fix that with no extra model.
"""
import re

from config.tts import LATIN_WORDS, LETTER_NAMES, MAX_LATIN_SHARE, NUMBER_WORDS, SCALE_WORDS, SYMBOL_WORDS

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
    """Integer -> words in the Indian system: 1,25,000 -> 'एक लाख पच्चीस हज़ार'."""
    words, scale = NUMBER_WORDS[lang], SCALE_WORDS[lang]
    if n < 100:
        return words[n]
    parts = []
    # WHY this order: Indian numbering groups as crore (10^7), lakh (10^5), thousand (10^3), hundred (10^2).
    for size, name in ((10**7, "crore"), (10**5, "lakh"), (10**3, "thousand"), (10**2, "hundred")):
        if n >= size:
            count, n = divmod(n, size)
            # crore can exceed 99 (e.g. 150 crore) -> recurse for the count
            parts.append(f"{number_to_words(count, lang)} {scale[name]}")
    if n:
        parts.append(words[n])
    return " ".join(parts)


def _say_number(match: re.Match, lang: str) -> str:
    rupee, digits, decimal, percent = match.groups()
    whole = int(digits.replace(",", ""))
    spoken = number_to_words(whole, lang)
    if decimal:
        # "2.5" -> "two point five": digit by digit after the point, as people say it.
        spoken += " " + SYMBOL_WORDS[lang]["."] + " " + " ".join(NUMBER_WORDS[lang][int(d)] for d in decimal[1:])
    if percent:
        spoken += " " + SYMBOL_WORDS[lang]["%"]
    if rupee:
        spoken += " " + SYMBOL_WORDS[lang]["₹"]   # ₹6,000 is said "six thousand rupees", so the word goes after
    return spoken


def _say_latin(match: re.Match, lang: str) -> str:
    token = match.group(0)
    known = LATIN_WORDS[lang].get(token.lower())
    if known:
        return known
    # FALLBACK: unknown English word or acronym -> spell it letter by letter rather than skip it silently.
    return " ".join(LETTER_NAMES[lang][c] for c in token.lower() if c in LETTER_NAMES[lang])


def normalize(text: str, lang: str) -> str:
    """Make an answer speakable by the AI4Bharat voice for `lang` ("gu" or "hi")."""
    if lang not in NUMBER_WORDS:
        raise ValueError(f"unsupported language: {lang}")
    text = CITATION.sub("", text)
    text = text.replace("।", ".").replace("॥", ".")   # WHY: the Hindi model's vocabulary has no danda; '.' still makes a pause
    text = NUMBER.sub(lambda m: _say_number(m, lang), text)
    text = LATIN_TOKEN.sub(lambda m: _say_latin(m, lang), text)
    text = re.sub(r"(?<=\S)-(?=\S)", " ", text)          # "PM-KISAN" -> two spoken words, not a minus sign
    for sym in ("&", "+", "/", "%", "₹"):
        text = text.replace(sym, f" {SYMBOL_WORDS[lang][sym]} ")
    return re.sub(r"\s+", " ", text).strip()
