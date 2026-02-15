"""
FastAPI app for Real-Time News Claim Verification.
POST /verify accepts a claim and returns verdict (Snopes-style taxonomy), reasoning, citations,
and optional confidence_note / conflict_mentioned. Out-of-scope claims return "Out of Scope" without retrieval.
"""
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory so uvicorn run from backend/ picks it up
load_dotenv(Path(__file__).resolve().parent / ".env")

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.pipeline import run_verification_pipeline, MAX_CLAIM_LENGTH
from agent.verify import VERDICT_UNPROVEN
from agent.web_retrieval import is_web_search_configured

app = FastAPI(
    title="Claim Verification API",
    description="Verify claims with citations. Verdicts: True, Mostly True, Mixture, Mostly False, False, Unproven, Out of Scope.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request / Response schemas ---

class VerifyRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CLAIM_LENGTH + 500,
        description="User-selected claim or headline to verify",
    )


class Citation(BaseModel):
    title: str
    url: str
    snippet: str


class VerifyResponse(BaseModel):
    verdict: str = Field(
        ...,
        description="One of: True, Mostly True, Mixture, Mostly False, False, Unproven, Out of Scope",
    )
    verdict_category: str = Field(
        ...,
        description="Same as verdict; alias for structured consumers",
    )
    reasoning: str = Field(..., description="Transparent explanation")
    citations: list[Citation] = Field(default_factory=list, description="Only real retrieved sources")
    evidence_count: int = Field(default=0, description="Number of evidence items considered")
    conflict_mentioned: bool = Field(default=False, description="True if sources conflict")
    confidence_note: Optional[str] = Field(default=None, description="E.g. limited evidence, conflicting sources")


@app.get("/health")
def health():
    """Reports API status and whether real-time web search is configured."""
    return {
        "status": "ok",
        "web_search_configured": is_web_search_configured(),
    }


@app.post("/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest):
    """
    Verify a claim using agentic RAG. In-scope claims get retrieval and verification;
    out-of-scope returns "Out of Scope" without retrieval. Headlines and headline-style text are in scope.
    """
    try:
        result = run_verification_pipeline(request.claim)
        return VerifyResponse(
            verdict=result["verdict"],
            verdict_category=result["verdict_category"],
            reasoning=result["reasoning"],
            citations=[Citation(**c) for c in result["citations"]],
            evidence_count=result.get("evidence_count", 0),
            conflict_mentioned=result.get("conflict_mentioned", False),
            confidence_note=result.get("confidence_note"),
        )
    except Exception as e:
        # Safe fallback: do not expose stack traces
        return VerifyResponse(
            verdict=VERDICT_UNPROVEN,
            verdict_category=VERDICT_UNPROVEN,
            reasoning="Verification could not be completed. Please try again.",
            citations=[],
            evidence_count=0,
            conflict_mentioned=False,
            confidence_note=None,
        )
