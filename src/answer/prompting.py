"""
COMPONENT : answer engine
PURPOSE   : Build the LLM prompt from retrieved passages, read the LLM's JSON reply, and check its citations.
INPUTS    : question, target language key, retrieved chunks; raw LLM reply text
OUTPUTS   : prompt string; parsed {answer, cited, answerable} or None; citation verdict
DEPENDS ON: config/answer.py (PROMPT_TEMPLATE, LANG_NAMES)
PANEL NOTE: The LLM only sees our passages, and a rule (not the LLM) checks that every [S#] it cites is real.
"""
import json
import re

from config.answer import LANG_NAMES, PROMPT_TEMPLATE

CITE_RE = re.compile(r"\[S(\d+)\]")
# WHY: Gemini often wraps JSON in ```json fences even when asked not to.
FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def build_prompt(query: str, target_key: str, chunks: list[dict]) -> str:
    """Prompt with passages labelled S1..Sk in retrieval order and the target language named in words."""
    passages = "\n\n".join(
        f"[S{i}] ({c['scheme_name']} · {c['section']})\n{c['text']}" for i, c in enumerate(chunks, start=1))
    return PROMPT_TEMPLATE.format(language=LANG_NAMES.get(target_key, "English"),
                                  passages=passages, query=query)


def parse_llm_output(text: str) -> dict | None:
    """Return {answer, cited, answerable} if the reply has exactly the right types, else None."""
    if not isinstance(text, str):
        # FALLBACK: a provider returned null content -> treat as unreadable (review #2).
        return None
    m = FENCE_RE.match(text)
    if m:
        text = m.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not (isinstance(data.get("answer"), str) and isinstance(data.get("answerable"), bool)
            and isinstance(data.get("cited"), list) and all(isinstance(c, str) for c in data["cited"])):
        return None
    return {"answer": data["answer"], "cited": data["cited"], "answerable": data["answerable"]}


def citations_valid(parsed: dict, k: int) -> bool:
    """An answerable reply must cite >=1 passage, only S1..Sk, and list every [S#] used in its text."""
    allowed = {f"S{i}" for i in range(1, k + 1)}
    cited = set(parsed["cited"])
    in_text = {f"S{n}" for n in CITE_RE.findall(parsed["answer"])}
    return bool(cited) and cited <= allowed and in_text <= cited
