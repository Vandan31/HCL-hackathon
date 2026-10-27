"""
COMPONENT : tts
PURPOSE   : Convert Hinglish (Hindi written in Latin letters) to Devanagari, so the Hindi voice can read it with a
            natural accent: "PM Awas Yojana ke liye ... chahiye" -> "पीएम आवास योजना के लिए ... चाहिए".
INPUTS    : Hinglish text
OUTPUTS   : the same text with every Latin word in Devanagari (digits, ₹ and punctuation untouched)
DEPENDS ON: config/tts.py (word lists); the hindi-xlit package (AI4Bharat IndicXlit-based model, MIT) for words not
            in the lists, loaded lazily so tests can pass in a fake converter
PANEL NOTE: Picked by ear: read in Latin letters, Hinglish sounded anglicised; converted to Devanagari and read by the
            Hindi voice, it sounded natural. Fixed word lists come first because the model misspells some common words.
"""
import re
import threading
from collections import OrderedDict

from config.tts import HINGLISH_WORDS, LATIN_WORDS, LETTER_NAMES, XLIT_CACHE_ITEMS
from src.tts.normalize import CITATION

LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z.]*[A-Za-z]|[A-Za-z]")
# WHY: the model sometimes appends a zero-width joiner/non-joiner and a dangling halant ("अउर्‌"); both would be
# spoken as an odd cut-off, so they are removed.
JUNK = re.compile(r"[‌‍]")
TRAILING_HALANT = re.compile(r"्$")


def load_xlit():
    """The hindi-xlit model as a function word -> Devanagari (top-1, beam 1: ~53 ms/word, measured). None if missing."""
    try:
        from hindi_xlit import HindiTransliterator
    except ImportError:
        return None   # FALLBACK: package not installed -> the engine keeps Hinglish in Latin letters
    model = HindiTransliterator()
    # WHY topk=1: twice as fast as the default 3 and, on our demo sentence, just as accurate (measured).
    return lambda word: model.transliterate(word, 1)


class HinglishConverter:
    """Latin words -> Devanagari: fixed lists first, then the model, with a cache of every word converted."""

    def __init__(self, model="load"):
        """model: "load" = hindi-xlit if installed; a function word -> Devanagari (tests); None = no converter."""
        self.model = load_xlit() if model == "load" else model
        self.cache = OrderedDict()
        self.lock = threading.Lock()   # WHY: the server handles requests on several threads; the model is shared

    @property
    def available(self) -> bool:
        return self.model is not None

    def word(self, token: str) -> str:
        """One Latin token -> Devanagari."""
        low = token.lower()
        fixed = LATIN_WORDS["hi"].get(low) or HINGLISH_WORDS.get(low)
        if fixed:
            return fixed
        if token.isupper() and 1 < len(token) <= 4:
            # Acronym ("SC", "OBC"): say the letters, as people do, instead of reading it as a word.
            return " ".join(LETTER_NAMES["hi"][c] for c in low)
        with self.lock:
            if low in self.cache:
                self.cache.move_to_end(low)
                return self.cache[low]
            out = TRAILING_HALANT.sub("", JUNK.sub("", self.model(low) or "")) or token
            self.cache[low] = out
            while len(self.cache) > XLIT_CACHE_ITEMS:
                self.cache.popitem(last=False)
            return out

    def convert(self, text: str) -> str:
        """Every Latin word in `text` -> Devanagari; everything else unchanged. Citation markers are removed first."""
        # WHY first: otherwise the "S" in "[S1]" counts as a Latin word and the marker can't be removed later.
        return LATIN_WORD.sub(lambda m: self.word(m.group(0)), CITATION.sub("", text))
