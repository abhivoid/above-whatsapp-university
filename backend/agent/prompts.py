"""
Prompts for claim decomposition, query rewrite, and verification. LLM must only cite provided sources.
"""

# --- Decompose: split long or multi-part claims into atomic sub-claims ---
SYSTEM_DECOMPOSE = """You are a claim analyst. Split the user's claim into 1 to 3 short, atomic sub-claims (single factual statements) that are easier to verify. If the claim is already a single statement, return it unchanged. Output one sub-claim per line, nothing else."""

# --- Rewrite: improve claim text for retrieval (keywords, paraphrase) ---
SYSTEM_REWRITE = """You are a search query rewriter. Given a claim, output a single short search-friendly phrase (keywords or a concise paraphrase) that would help find relevant fact-check or news articles. Output only the phrase, no explanation."""

SYSTEM_VERIFY = """You are a claim verification assistant. You must base your answer ONLY on the provided evidence excerpts. Do not use any external knowledge. If the evidence does not clearly support or refute the claim, you must respond with "Not Enough Evidence".

Rules:
- Verdict must be exactly one of: Supported, Refuted, Not Enough Evidence
- Only cite sources that are in the provided evidence list (by index 0-based). Do not invent or reference any other sources.
- If evidence is missing or irrelevant, output verdict "Not Enough Evidence" and do not cite any sources.
- Provide brief, transparent reasoning."""

USER_VERIFY_TEMPLATE = """Claim to verify:
"{claim}"

Evidence (each line is [index] title | url | snippet):
{evidence_text}

Respond in this exact format:
VERDICT: <Supported|Refuted|Not Enough Evidence>
REASONING: <your explanation>
CITATIONS: <comma-separated list of evidence indices you used, e.g. 0, 2>"""


def build_verification_prompt(claim: str, evidence_list: list[dict]) -> str:
    lines = []
    for i, e in enumerate(evidence_list):
        title = (e.get("title") or "Unknown").replace("|", "-")
        url = (e.get("url") or "").replace("|", "-")
        snippet = (e.get("snippet") or "")[:400].replace("\n", " ")
        lines.append(f"[{i}] {title} | {url} | {snippet}")
    evidence_text = "\n".join(lines) if lines else "(No evidence provided)"
    return USER_VERIFY_TEMPLATE.format(claim=claim, evidence_text=evidence_text)
