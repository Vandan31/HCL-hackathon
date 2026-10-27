"""
COMPONENT : answer engine
PURPOSE   : The fixed "I don't know" messages, one per input language, each with a next step for the citizen.
INPUTS    : detected lang, code_mixed flag, refusal reason
OUTPUTS   : a refusal dict in the answer() contract shape
DEPENDS ON: nothing
PANEL NOTE: Refusals are templates, never LLM text, so they can't hallucinate and always read the same.
"""

# WHY: refusal is always in the language of the input (Harsh's decision), so one template per language.
# No helpline numbers: none has been verified by a human yet.
TEMPLATES = {
    "en": (
        "I could not find this in my scheme documents, so I can't answer it reliably. "
        "Please check myscheme.gov.in or visit your nearest CSC (Common Service Centre)."
    ),
    "hi": (
        "मुझे यह जानकारी मेरे योजना दस्तावेज़ों में नहीं मिली, इसलिए मैं इसका भरोसेमंद उत्तर नहीं दे सकता। "
        "कृपया myscheme.gov.in देखें या अपने नज़दीकी CSC (कॉमन सर्विस सेंटर) पर जाएँ।"
    ),
    "hinglish": (
        "Mujhe yeh jaankari meri scheme documents mein nahi mili, isliye main iska pakka jawab nahi de sakta. "
        "Kripya myscheme.gov.in dekhein ya apne nazdeeki CSC (Common Service Centre) par jaayein."
    ),
    # Wording checked by a native speaker (gu; confirmed by Harsh, 2026-10-27)
    "gu": (
        "મને આ માહિતી મારા યોજના દસ્તાવેજોમાં મળી નથી, તેથી હું તેનો વિશ્વસનીય જવાબ આપી શકતો નથી. "
        "કૃપા કરીને myscheme.gov.in જુઓ અથવા તમારા નજીકના CSC (કોમન સર્વિસ સેન્ટર) ની મુલાકાત લો."
    ),
    # Wording checked by a native speaker (mr; confirmed by Harsh, 2026-10-27)
    "mr": (
        "मला ही माहिती माझ्या योजना कागदपत्रांमध्ये सापडली नाही, त्यामुळे मी याचे विश्वासार्ह उत्तर देऊ शकत नाही. "
        "कृपया myscheme.gov.in पहा किंवा तुमच्या जवळच्या CSC (कॉमन सर्व्हिस सेंटर) ला भेट द्या."
    ),
    # Wording checked by a native speaker (ta; confirmed by Harsh, 2026-10-27)
    "ta": (
        "இந்தத் தகவல் என் திட்ட ஆவணங்களில் இல்லை, எனவே இதற்கு நம்பகமான பதில் தர முடியாது. "
        "தயவுசெய்து myscheme.gov.in ஐப் பார்க்கவும் அல்லது அருகிலுள்ள CSC (பொது சேவை மையம்) க்குச் செல்லவும்."
    ),
}


def template_key(lang: str, code_mixed: bool) -> str:
    """Map detector output to a template key; Hindi typed in Roman script (Hinglish) gets its own key."""
    return "hinglish" if lang == "hi" and code_mixed else lang


def refusal(lang: str, code_mixed: bool, reason: str) -> dict:
    """Build a refusal in the answer() contract shape, worded in the asker's language."""
    # FALLBACK: a language we have no template for (detector returned something new) -> English text.
    text = TEMPLATES.get(template_key(lang, code_mixed), TEMPLATES["en"])
    return {"answer": text, "lang": lang, "refused": True, "refusal_reason": reason,
            "citations": [], "confidence": 0.0}
