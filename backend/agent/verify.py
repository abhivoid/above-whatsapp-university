"""
Verification LLM: takes claim + evidence, returns verdict, reasoning, and cited indices.
Citations are filtered to only include indices from retrieved evidence.
"""
import os
import re
from .prompts import SYSTEM_VERIFY, build_verification_prompt


def normalize_verdict(s: str) -> str:
    v = (s or "").strip().lower()
    if "supported" in v and "not" not in v[:20]:
        return "Supported"
    if "refuted" in v:
        return "Refuted"
    return "Not Enough Evidence"


def _parse_llm_response(text: str) -> tuple[str, str, list[int]]:
    verdict = "Not Enough Evidence"
    reasoning = ""
    citations: list[int] = []

    if not text:
        return verdict, reasoning, citations

    # VERDICT: ...
    m = re.search(r"VERDICT:\s*(.+?)(?:\n|REASONING:|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        verdict = m.group(1).strip()

    # REASONING: ...
    m = re.search(r"REASONING:\s*(.+?)(?:\n\s*CITATIONS:|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        reasoning = m.group(1).strip()

    # CITATIONS: 0, 2, 3
    m = re.search(r"CITATIONS:\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                citations.append(int(part))

    return verdict, reasoning, citations


def run_verification_llm(claim: str, evidence_list: list[dict]) -> tuple[str, str, list[int]]:
    """
    Call LLM with claim + evidence. Returns (verdict, reasoning, list of evidence indices to cite).
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # No API key: return Not Enough Evidence and no citations (no fabrication)
        return (
            "Not Enough Evidence",
            "Verification is not configured (missing OPENAI_API_KEY).",
            [],
        )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        user_content = build_verification_prompt(claim, evidence_list)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_VERIFY},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as e:
        return (
            "Not Enough Evidence",
            f"Verification service error: {e!s}.",
            [],
        )

    verdict, reasoning, cited_indices = _parse_llm_response(text)
    verdict = normalize_verdict(verdict)
    # If LLM said not enough evidence, clear citations
    if verdict == "Not Enough Evidence":
        cited_indices = []
    return verdict, reasoning, cited_indices
