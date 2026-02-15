"""
Claim classifier (guardrail): pre-retrieval step that classifies input as
IN_SCOPE (verifiable factual claim) or OUT_OF_SCOPE (no retrieval/verification).
News headlines and headline-style text are always IN_SCOPE. When in doubt, prefer IN_SCOPE.
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

IN_SCOPE = "IN_SCOPE"
OUT_OF_SCOPE = "OUT_OF_SCOPE"

CLASSIFIER_SYSTEM = """You are a claim scope classifier for a fact-checking system. Your job is to decide whether the user's input is a verifiable factual claim (IN_SCOPE) or not (OUT_OF_SCOPE).

CRITICAL RULES:
- News headlines and headline-style titles are IN_SCOPE even if they contain words like "what", "why", or "how". These are still verifiable factual claims (e.g. that an event is happening, or what is at stake).
- Only mark OUT_OF_SCOPE for: direct questions asking for information (e.g. "What is the capital of France?"), personal statements or identity (e.g. "I am gay", "I went to the park"), pure opinions or value judgments (e.g. "Coffee is the best drink"), greetings or chitchat (e.g. "Hello", "How are you?"), requests for advice/recommendations (e.g. "What should I buy?"), or clearly non-factual text.
- When in doubt, prefer IN_SCOPE. If you are uncertain, return IN_SCOPE and let retrieval and verification handle it. Avoid blocking borderline cases.

IN_SCOPE examples (these must be classified IN_SCOPE):
- "Bangladesh to vote tomorrow: What's at stake for India, Pakistan and China"
- "Why the Fed raised rates again"
- "How the new law affects small businesses"
- "What we know about the earthquake in Turkey"
- "GDP grew 3% in 2024"
- "The earth is flat" (verifiable factual claim, even if false)
- Any headline or news title the user pastes to verify

OUT_OF_SCOPE examples:
- "I am gay" (personal statement)
- "What is the capital of France?" (direct question asking for information)
- "Coffee is the best drink" (opinion)
- "Hello" (greeting)
- "What should I buy?" (request for advice)

Output exactly one line: either IN_SCOPE or OUT_OF_SCOPE. Nothing else."""


def classify_claim(claim: str) -> str:
    """
    Classify claim as IN_SCOPE or OUT_OF_SCOPE.
    On API failure or missing key, returns IN_SCOPE (prefer not to block).
    """
    claim = (claim or "").strip()
    if not claim:
        return OUT_OF_SCOPE

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("Classifier: no OPENAI_API_KEY, defaulting to IN_SCOPE")
        return IN_SCOPE

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM},
                {"role": "user", "content": claim},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        text = (response.choices[0].message.content or "").strip().upper()
    except Exception as e:
        logger.warning("Classifier API error: %s, defaulting to IN_SCOPE", e)
        return IN_SCOPE

    if OUT_OF_SCOPE in text:
        return OUT_OF_SCOPE
    return IN_SCOPE
