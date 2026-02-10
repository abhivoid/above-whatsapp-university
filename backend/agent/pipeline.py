"""
Agentic RAG pipeline: decompose (optional) -> retrieve (with optional rewrite retry) -> verify.
Returns verdict, reasoning, and citations only from retrieved evidence.
"""
from .retrieval import retrieve_evidence, merge_evidence
from .prompts import build_verification_prompt
from .verify import run_verification_llm, normalize_verdict
from .llm_helpers import decompose_claim, rewrite_query_for_retrieval


def run_verification_pipeline(claim: str) -> dict:
    """
    Run full pipeline: optionally decompose -> retrieve (with optional rewrite retry) -> verify.
    If no evidence: return "Not Enough Evidence" and empty citations.
    """
    claim = (claim or "").strip()
    if not claim:
        return {
            "verdict": "Not Enough Evidence",
            "reasoning": "No claim was provided.",
            "citations": [],
        }

    # 1) Optional decomposition: get atomic sub-claims for multi-part claims
    queries = decompose_claim(claim)
    if not queries:
        queries = [claim]

    # 2) Retrieve evidence for each query (main + sub-claims)
    all_evidence: list[list[dict]] = []
    for q in queries[:3]:
        all_evidence.append(retrieve_evidence(q, max_chunks=5))

    # 3) Agentic: if first round returned few results, rewrite and retry once
    if len(all_evidence) > 0 and len(all_evidence[0]) < 3:
        rewritten = rewrite_query_for_retrieval(claim)
        if rewritten and rewritten.lower() != claim.lower()[:200]:
            all_evidence.append(retrieve_evidence(rewritten, max_chunks=5))

    evidence_list = merge_evidence(all_evidence)
    evidence_list = evidence_list[:15]

    # 4) If no evidence, do not call LLM for citations
    if not evidence_list:
        return {
            "verdict": "Not Enough Evidence",
            "reasoning": "No relevant evidence was found in the knowledge base or search results to support or refute this claim.",
            "citations": [],
        }

    # 5) Run verification LLM (verdict + reasoning + which sources to cite)
    raw_verdict, reasoning, cited_indices = run_verification_llm(claim, evidence_list)

    # 6) Build citations only from retrieved evidence (no fabrication)
    verdict = normalize_verdict(raw_verdict)
    if verdict == "Not Enough Evidence":
        citations = []
    else:
        citations = [
            {"title": evidence_list[i]["title"], "url": evidence_list[i]["url"], "snippet": evidence_list[i]["snippet"]}
            for i in cited_indices
            if 0 <= i < len(evidence_list)
        ]

    return {
        "verdict": verdict,
        "reasoning": reasoning or "No reasoning provided.",
        "citations": citations,
    }
