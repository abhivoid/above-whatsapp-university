"""
Verification LLM: takes claim + evidence, returns verdict, reasoning, cited indices,
and optional confidence_note / conflict_mentioned. Uses Snopes-style verdict taxonomy.
"""
import os
import re
from .prompts import SYSTEM_VERIFY, build_verification_prompt, VERDICTS_FACTUAL

# Canonical verdicts; normalize_verdict maps LLM output to one of these
VERDICT_UNPROVEN = "Unproven"
VERDICT_OUT_OF_SCOPE = "Out of Scope"


def normalize_verdict(s: str) -> str:
    """Map LLM verdict string to canonical taxonomy: True, Mostly True, Mixture, Mostly False, False, Unproven."""
    v = (s or "").strip()
    v_lower = v.lower()
    # Legacy mappings
    if "supported" in v_lower and "not" not in v_lower[:25]:
        return "True"
    if "refuted" in v_lower:
        return "False"
    if "not enough evidence" in v_lower or "unproven" in v_lower:
        return VERDICT_UNPROVEN
    # Match new taxonomy (case-insensitive)
    for canonical in VERDICTS_FACTUAL:
        if canonical.lower() in v_lower or v_lower == canonical.lower():
            return canonical
    return VERDICT_UNPROVEN


def _parse_llm_response(text: str) -> tuple[str, str, list[int], bool, str]:
    verdict = VERDICT_UNPROVEN
    reasoning = ""
    citations: list[int] = []
    conflict_mentioned = False
    confidence_note = ""

    if not text:
        return verdict, reasoning, citations, conflict_mentioned, confidence_note

    # VERDICT: ...
    m = re.search(r"VERDICT:\s*(.+?)(?:\n|REASONING:|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        verdict = m.group(1).strip()

    # REASONING: ...
    m = re.search(r"REASONING:\s*(.+?)(?:\n\s*CITATIONS:|\n\s*CONFLICT|\n\s*CONFIDENCE|$)", text, re.IGNORECASE | re.DOTALL)
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

    # CONFLICT_MENTIONED: yes
    m = re.search(r"CONFLICT_MENTIONED:\s*(\w+)", text, re.IGNORECASE)
    if m and m.group(1).strip().lower() == "yes":
        conflict_mentioned = True

    # CONFIDENCE_NOTE: ...
    m = re.search(r"CONFIDENCE_NOTE:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        confidence_note = m.group(1).strip()

    return verdict, reasoning, citations, conflict_mentioned, confidence_note


def run_verification_llm(
    claim: str, evidence_list: list[dict]
) -> tuple[str, str, list[int], bool, str]:
    """
    Call LLM with claim + evidence. Returns (verdict, reasoning, cited_indices, conflict_mentioned, confidence_note).
    On API failure or missing key, returns safe Unproven with no fabrication.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return (
            VERDICT_UNPROVEN,
            "Verification is not configured (missing OPENAI_API_KEY).",
            [],
            False,
            "",
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
            VERDICT_UNPROVEN,
            "Verification service temporarily unavailable.",
            [],
            False,
            "",
        )

    verdict, reasoning, cited_indices, conflict_mentioned, confidence_note = _parse_llm_response(text)
    verdict = normalize_verdict(verdict)
    if verdict == VERDICT_UNPROVEN:
        cited_indices = []
    return verdict, reasoning, cited_indices, conflict_mentioned, confidence_note
