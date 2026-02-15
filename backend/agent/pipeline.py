"""
Agentic RAG pipeline: guardrail (classifier) -> decompose -> retrieve (KB + web) -> verify.
Only in-scope claims run retrieval and verification; out-of-scope returns "Out of Scope" without retrieval.
Returns verdict (Snopes-style taxonomy), reasoning, citations, and optional confidence_note / conflict_mentioned.
"""
from __future__ import annotations
import logging
from .classifier import classify_claim, IN_SCOPE, OUT_OF_SCOPE
from .retrieval import retrieve_evidence, merge_evidence
from .web_retrieval import search_web
from .verify import run_verification_llm, VERDICT_UNPROVEN, VERDICT_OUT_OF_SCOPE

from .llm_helpers import decompose_claim, rewrite_query_for_retrieval

logger = logging.getLogger(__name__)

# Limits and caps
MAX_CLAIM_LENGTH = 2000
MIN_CLAIM_LENGTH = 2
WEB_RESULTS_PER_QUERY = 10
MAX_TOTAL_EVIDENCE = 20


def _normalize_claim(claim: str) -> str:
    """Trim and cap length; return empty if too short or invalid."""
    s = (claim or "").strip()
    if len(s) < MIN_CLAIM_LENGTH:
        return ""
    return s[:MAX_CLAIM_LENGTH]


def run_verification_pipeline(claim: str) -> dict:
    """
    Run full pipeline: normalize -> classify -> (if in scope) decompose -> retrieve -> verify.
    Out-of-scope: return "Out of Scope" and skip retrieval.
    Empty/no evidence: return "Unproven" without calling generator.
    """
    raw_claim = (claim or "").strip()
    claim = _normalize_claim(raw_claim)
    if not claim:
        return _structured_response(
            VERDICT_UNPROVEN,
            "Input is too short or empty to verify.",
            [],
            evidence_count=0,
            confidence_note="Input too short.",
        )

    # 1) Guardrail: classify in-scope vs out-of-scope
    scope = classify_claim(claim)
    logger.info("guardrail_decision scope=%s claim_len=%d", scope, len(claim))
    if scope == OUT_OF_SCOPE:
        return _structured_response(
            VERDICT_OUT_OF_SCOPE,
            "This input is not a verifiable factual claim. It may be a personal statement, opinion, greeting, or direct question for information. Only factual claims about events, numbers, or states of the world can be verified.",
            [],
            evidence_count=0,
        )

    # 2) Optional decomposition
    queries = decompose_claim(claim)
    if not queries:
        queries = [claim]

    # 3) Retrieve from KB and web (with fallback: if web fails, KB-only is still used)
    all_evidence: list[list[dict]] = []
    for q in queries[:3]:
        kb_chunks = retrieve_evidence(q, max_chunks=5)
        all_evidence.append(kb_chunks)
        try:
            web_results = search_web(q, max_results=WEB_RESULTS_PER_QUERY)
            if web_results:
                all_evidence.append(web_results)
        except Exception as e:
            logger.warning("web_search_fallback error=%s query=%s", e, q[:50])

    # 4) Optional rewrite retry if few results
    if all_evidence and len(all_evidence[0]) < 3:
        rewritten = rewrite_query_for_retrieval(claim)
        if rewritten and rewritten.lower() != claim.lower()[:200]:
            all_evidence.append(retrieve_evidence(rewritten, max_chunks=5))
            try:
                web_rewritten = search_web(rewritten, max_results=WEB_RESULTS_PER_QUERY)
                if web_rewritten:
                    all_evidence.append(web_rewritten)
            except Exception:
                pass

    evidence_list = merge_evidence(all_evidence, dedupe_by_snippet=True)
    evidence_list = evidence_list[:MAX_TOTAL_EVIDENCE]
    retrieval_count = len(evidence_list)
    logger.info("retrieval_stats evidence_count=%d", retrieval_count)

    # 5) Empty evidence: do not call generator; return Unproven
    if not evidence_list:
        return _structured_response(
            VERDICT_UNPROVEN,
            "No relevant evidence was found in the knowledge base or search results to support or refute this claim.",
            [],
            evidence_count=0,
        )

    # 6) Run verification LLM (verdict, reasoning, cited indices, conflict_mentioned, confidence_note)
    verdict, reasoning, cited_indices, conflict_mentioned, confidence_note = run_verification_llm(
        claim, evidence_list
    )
    if verdict == VERDICT_UNPROVEN:
        citations = []
    else:
        citations = [
            {
                "title": evidence_list[i].get("title", "Unknown"),
                "url": evidence_list[i].get("url", ""),
                "snippet": evidence_list[i].get("snippet", ""),
            }
            for i in cited_indices
            if 0 <= i < len(evidence_list)
        ]

    return _structured_response(
        verdict,
        reasoning or "No reasoning provided.",
        citations,
        evidence_count=retrieval_count,
        conflict_mentioned=conflict_mentioned,
        confidence_note=confidence_note or None,
    )


def _structured_response(
    verdict: str,
    reasoning: str,
    citations: list[dict],
    *,
    evidence_count: int = 0,
    conflict_mentioned: bool = False,
    confidence_note: str | None = None,
) -> dict:
    """Build API response with verdict, reasoning, citations, and optional fields."""
    return {
        "verdict": verdict,
        "verdict_category": verdict,
        "reasoning": reasoning,
        "citations": citations,
        "evidence_count": evidence_count,
        "conflict_mentioned": conflict_mentioned,
        "confidence_note": confidence_note,
    }
