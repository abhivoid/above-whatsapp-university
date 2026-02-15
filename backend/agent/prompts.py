"""
Prompts for claim decomposition, query rewrite, and verification. LLM must only cite provided sources.
Verdict taxonomy: True, Mostly True, Mixture, Mostly False, False, Unproven (Snopes-style).
"""

# Verdict taxonomy (fact-checking standard); Out of Scope is set by guardrail, not generator
VERDICTS_FACTUAL = (
    "True",
    "Mostly True",
    "Mixture",
    "Mostly False",
    "False",
    "Unproven",
)

# --- Decompose: split long or multi-part claims into atomic sub-claims ---
SYSTEM_DECOMPOSE = """You are a claim analyst. Split the user's claim into 1 to 3 short, atomic sub-claims (single factual statements) that are easier to verify. If the claim is already a single statement, return it unchanged. Output one sub-claim per line, nothing else."""

# --- Rewrite: improve claim text for retrieval (keywords, paraphrase) ---
SYSTEM_REWRITE = """You are a search query rewriter. Given a claim, output a single short search-friendly phrase (keywords or a concise paraphrase) that would help find relevant fact-check or news articles. Output only the phrase, no explanation."""

SYSTEM_VERIFY = """You are a claim verification assistant. Base your answer ONLY on the provided evidence excerpts. Do not use external knowledge or fabricate facts. If the evidence does not clearly support or refute the claim, respond with "Unproven".

Verdict taxonomy (use exactly one):
- True — factually correct according to evidence.
- Mostly True — largely correct with minor inaccuracies.
- Mixture — some parts true, some false or unverified; state the conflict clearly.
- Mostly False — largely incorrect with some true elements.
- False — factually incorrect according to evidence.
- Unproven — evidence does not clearly support or refute; use when evidence is missing, irrelevant, conflicting without clear preponderance, or from a single weak source.

Rules:
- Verdict must be exactly one of: True, Mostly True, Mixture, Mostly False, False, Unproven.
- Only cite sources from the provided evidence list (by 0-based index). Do not invent sources.
- If all evidence is irrelevant or absent, output Unproven and do not cite.
- If sources conflict, use Mixture or Unproven and mention the conflict in reasoning. Optionally add CONFLICT_MENTIONED: yes.
- If relying on a single or weak source, prefer Unproven or Mostly True/Mostly False and add CONFIDENCE_NOTE: limited evidence (or similar).
- Provide brief, transparent reasoning."""

USER_VERIFY_TEMPLATE = """Claim to verify:
"{claim}"

Evidence (each line is [index] title | url | snippet):
{evidence_text}

Respond in this exact format:
VERDICT: <True|Mostly True|Mixture|Mostly False|False|Unproven>
REASONING: <your explanation>
CITATIONS: <comma-separated list of evidence indices you used, e.g. 0, 2>
Optional (include when applicable):
CONFLICT_MENTIONED: <yes|no>
CONFIDENCE_NOTE: <e.g. limited evidence, conflicting sources, or leave blank>"""


def build_verification_prompt(claim: str, evidence_list: list[dict]) -> str:
    lines = []
    for i, e in enumerate(evidence_list):
        title = (e.get("title") or "Unknown").replace("|", "-")
        url = (e.get("url") or "").replace("|", "-")
        snippet = (e.get("snippet") or "")[:400].replace("\n", " ")
        lines.append(f"[{i}] {title} | {url} | {snippet}")
    evidence_text = "\n".join(lines) if lines else "(No evidence provided)"
    return USER_VERIFY_TEMPLATE.format(claim=claim, evidence_text=evidence_text)
