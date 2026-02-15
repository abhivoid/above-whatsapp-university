# Technical overview

This document gives a short technical explanation of the Real-Time News Claim Verification Assistant: components, configuration, and how they fit together.

## Architecture in brief

- **Client**: Chrome extension (Manifest V3). User selects text → context menu "Verify claim" → popup sends the claim to the backend and displays verdict + citations.
- **Backend**: FastAPI app exposing `POST /verify` and `GET /health`. The verification path is an **agentic RAG** pipeline: guardrail (classifier) → optional decomposition → retrieval (ChromaDB + optional web search) → optional query-rewrite retry → LLM verification with strict citation rules.
- **RAG**: Evidence comes only from retrieval (vector store and/or web). The LLM never invents sources; empty evidence yields "Unproven" with no citations.
- **Guardrail**: A pre-retrieval classifier marks input as **in scope** (factual claim) or **out of scope**. Only in-scope claims run retrieval and verification; out-of-scope returns "Out of Scope" without calling retrieval or the verification LLM.

## Configuration (environment variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (for verification) | OpenAI API key for LLM calls. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`). |
| `CHROMA_PERSIST_DIR` | No | Path for ChromaDB data (default: `backend/chroma_data`). |
| `SERPER_API_KEY` | No (for web search) | [Serper](https://serper.dev) API key for real-time web search. If set, evidence is fetched from the web in addition to the KB. |
| `TAVILY_API_KEY` | No (for web search) | [Tavily](https://tavily.com) API key. Used only when `SERPER_API_KEY` is not set. Same role as Serper. |

- Without `OPENAI_API_KEY`, the API still runs but returns "Unproven" with a message that verification is not configured; the classifier defaults to in scope so retrieval still runs.
- Without `SERPER_API_KEY` or `TAVILY_API_KEY`, verification uses only the ChromaDB knowledge base (and returns "Unproven" when no evidence is found).

## Pipeline flow (high level)

1. **Normalize** — Trim and cap claim length; reject too-short input → Unproven.
2. **Classify** — LLM guardrail: IN_SCOPE vs OUT_OF_SCOPE. OUT_OF_SCOPE → return "Out of Scope", no retrieval.
3. **Decompose** — Optional: split long/multi-part claim into 1–3 sub-claims for better retrieval.
4. **Retrieve** — For each (sub-)query: ChromaDB (sentence-transformers embedding) + optional web (Serper or Tavily). Merge and dedupe (URL + snippet).
5. **Rewrite retry** — If evidence is sparse, optionally rewrite the claim as a search query and run retrieval again; merge into evidence list.
6. **Empty evidence** — If no evidence after merge → return "Unproven", no LLM call.
7. **Verify** — Single LLM call with claim + numbered evidence; strict prompt for Snopes-style verdict, reasoning, and citation indices. Citations are built only from those indices; no fabrication.

## Key components (code)

| Layer | Role |
|-------|------|
| `extension/` | Popup UI, context menu, HTTP client to backend `/verify`. |
| `backend/main.py` | FastAPI app, request/response models, error handling (safe Unproven on failure). |
| `backend/agent/classifier.py` | Scope guardrail: IN_SCOPE / OUT_OF_SCOPE. |
| `backend/agent/pipeline.py` | Orchestrates: classify → decompose → retrieve → merge → verify; caps and limits. |
| `backend/agent/retrieval.py` | ChromaDB + sentence-transformers; `merge_evidence` (URL/snippet dedupe). |
| `backend/agent/web_retrieval.py` | Serper / Tavily; returns `{title, url, snippet}`. |
| `backend/agent/llm_helpers.py` | Decompose claim, rewrite query for retrieval. |
| `backend/agent/verify.py` | Verification LLM; verdict normalization; parse VERDICT/REASONING/CITATIONS/CONFLICT/CONFIDENCE. |
| `backend/agent/prompts.py` | System/user prompts for classifier, decompose, rewrite, verify. |
| `backend/kb/ingest.py` | Embed and index documents into ChromaDB; used offline to seed the KB. |

For a visual architecture diagram (RAG + agent flow + components), see [ARCHITECTURE.md](./ARCHITECTURE.md).
