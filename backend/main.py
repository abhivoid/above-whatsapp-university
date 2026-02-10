"""
FastAPI app for Real-Time News Claim Verification.
POST /verify accepts a claim and returns verdict, reasoning, and citations.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.pipeline import run_verification_pipeline

app = FastAPI(
    title="Claim Verification API",
    description="Verify claims with citations; returns Not Enough Evidence when no sources found.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Extension and localhost; tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response schemas ---

class VerifyRequest(BaseModel):
    claim: str = Field(..., min_length=1, description="User-selected claim to verify")


class Citation(BaseModel):
    title: str
    url: str
    snippet: str


class VerifyResponse(BaseModel):
    verdict: str = Field(..., description="One of: Supported, Refuted, Not Enough Evidence")
    reasoning: str = Field(..., description="Transparent explanation")
    citations: list[Citation] = Field(default_factory=list, description="Only real retrieved sources")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/verify", response_model=VerifyResponse)
def verify(request: VerifyRequest):
    """
    Verify a claim using agentic RAG. Returns verdict with citations.
    If no sufficient evidence, returns "Not Enough Evidence" and empty citations.
    """
    result = run_verification_pipeline(request.claim)
    return VerifyResponse(
        verdict=result["verdict"],
        reasoning=result["reasoning"],
        citations=[Citation(**c) for c in result["citations"]],
    )
