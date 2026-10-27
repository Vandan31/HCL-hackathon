"""
COMPONENT : answer engine
PURPOSE   : Attach the pre-made IndicTrans2 translation under each cited passage, in the user's language.
INPUTS    : data/processed/translations.jsonl (made offline on PARAM), retrieved chunks, user language
OUTPUTS   : citation dicts for the UI's source cards
DEPENDS ON: the offline IndicTrans2 job (black box, Vandan) for the jsonl file
PANEL NOTE: The original passage is always shown as the official text; IndicTrans2 only helps the user read it.
"""
import json


def load_translations(path: str) -> dict[tuple[str, str], str]:
    """Read translations.jsonl into {(chunk_id, lang): text}; loaded once at startup."""
    table: dict[tuple[str, str], str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    table[(row["chunk_id"], row["lang"])] = row["text"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    # FALLBACK: one bad line from the offline job must not kill every translation.
                    continue
    except FileNotFoundError:
        # FALLBACK: translations not generated yet -> cards show the original passage only.
        return {}
    return table


def translation_target(lang: str, code_mixed: bool) -> str:
    """Which language the card translation should be in; Hinglish users read Hindi (Devanagari)."""
    # WHY: IndicTrans2 can't output Hinglish, and Hinglish speakers read Hindi (Harsh's decision).
    # code_mixed is kept in the signature so the rule lives here if it ever changes.
    return lang


def build_citation(sid: str, chunk: dict, user_lang: str, code_mixed: bool,
                   translations: dict[tuple[str, str], str]) -> dict:
    """One source card: the original passage, plus a translation when its language differs from the user's."""
    target = translation_target(user_lang, code_mixed)
    translation = None
    if chunk["lang"] != target:
        # FALLBACK: missing row -> None; the UI shows "translation not available" under the original.
        translation = translations.get((chunk["chunk_id"], target))
    return {
        "id": sid,
        "chunk_id": chunk["chunk_id"],
        "scheme_name": chunk["scheme_name"],
        "passage": chunk["text"],
        "source_url": chunk["source_url"],
        "passage_lang": chunk["lang"],
        "translation": translation,
        "translation_lang": target if translation is not None else None,
    }
