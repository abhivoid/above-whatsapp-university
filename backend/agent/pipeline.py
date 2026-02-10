"""
Agentic RAG pipeline: decompose (optional) -> retrieve (KB + web) (with optional rewrite retry) -> verify.
Returns verdict, reasoning, and citations only from retrieved evidence.
Evidence is gathered from ChromaDB and from real-time web search (Serper/Tavily) when configured.
"""
from .retrieval import retrieve_evidence, merge_evidence
from .web_retrieval import search_web
from .prompts import build_verification_prompt
from .verify import run_verification_llm, normalize_verdict
from .llm_helpers import decompose_claim, rewrite_query_for_retrieval

# Max web results per query; total evidence is capped below
WEB_RESULTS_PER_QUERY = 10
MAX_TOTAL_EVIDENCE = 20


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

    # 2) Retrieve evidence for each query from both ChromaDB and the web
    all_evidence: list[list[dict]] = []
    for q in queries[:3]:
        kb_chunks = retrieve_evidence(q, max_chunks=5)
        all_evidence.append(kb_chunks)
        web_results = search_web(q, max_results=WEB_RESULTS_PER_QUERY)
        if web_results:
            all_evidence.append(web_results)

    # 3) Agentic: if first round returned few results, rewrite and retry once (KB + web)
    if len(all_evidence) > 0 and len(all_evidence[0]) < 3:
        rewritten = rewrite_query_for_retrieval(claim)
        if rewritten and rewritten.lower() != claim.lower()[:200]:
            all_evidence.append(retrieve_evidence(rewritten, max_chunks=5))
            web_rewritten = search_web(rewritten, max_results=WEB_RESULTS_PER_QUERY)
            if web_rewritten:
                all_evidence.append(web_rewritten)

    evidence_list = merge_evidence(all_evidence)
    evidence_list = evidence_list[:MAX_TOTAL_EVIDENCE]

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
            {
                "title": evidence_list[i].get("title", "Unknown"),
                "url": evidence_list[i].get("url", ""),
                "snippet": evidence_list[i].get("snippet", ""),
            }
            for i in cited_indices
            if 0 <= i < len(evidence_list)
        ]

    return {
        "verdict": verdict,
        "reasoning": reasoning or "No reasoning provided.",
        "citations": citations,
    }
