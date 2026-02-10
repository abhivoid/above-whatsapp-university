"""
LLM helpers for agentic steps: decompose claim, rewrite query for retrieval.
"""
import os
from .prompts import SYSTEM_DECOMPOSE, SYSTEM_REWRITE


def _call_llm(system: str, user: str, max_tokens: int = 200) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def decompose_claim(claim: str) -> list[str]:
    """
    Split long or multi-part claim into atomic sub-claims (1–3). Returns list of strings.
    If decomposition fails or claim is short, returns [claim].
    """
    if not (claim or "").strip():
        return []
    claim = claim.strip()
    if len(claim) < 120:
        return [claim]
    text = _call_llm(SYSTEM_DECOMPOSE, claim)
    if not text:
        return [claim]
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return [claim]
    return lines[:3]


def rewrite_query_for_retrieval(claim: str) -> str:
    """
    Return a short search-friendly phrase for better retrieval. Empty string on failure.
    """
    if not (claim or "").strip():
        return ""
    text = _call_llm(SYSTEM_REWRITE, claim, max_tokens=100)
    return (text or "").strip()[:200]
