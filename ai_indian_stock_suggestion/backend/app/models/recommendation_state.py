"""Typed state produced by recommendation pipeline agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchOutputState(BaseModel):
    """Single stock pick from stock_research agent (one object per suggestion)."""

    date: datetime
    customer_id: str = Field(description="Customer id aligned with users table rows for this email")
    budget: float
    stock_code: str = Field(description="Suggested NSE ticker, uppercase")
    research: str


class BehaviourAnalysisOutput(BaseModel):
    date: datetime
    customer_id: str
    behaviour_analysis: str


class RecommendationOutputState(BaseModel):
    """Per-stock consolidated recommendation."""

    date: datetime
    customer_id: str
    stock_code: str
    recommendation: str
    quantity: int = Field(ge=1, description="Suggested number of shares to buy given budget framing")
    time_period: str = Field(description="Suggested holding horizon (text, e.g. 6–12 months)")


class StockRecommendationRecord(BaseModel):
    """Stored document shape for stock_recommendations collection."""

    customer_id: str
    date: datetime
    budget: float
    recommendation: dict[str, int] = Field(
        ...,
        description="Map of suggested stock_code to integer quantity",
    )


class RecommendationPipelineResult(BaseModel):
    """Full pipeline result; nested rows include customer_id for DB / internal use."""

    pipeline_status: Literal["ok", "skipped_no_api_key", "error"]
    recommendation: dict[str, int] = Field(
        default_factory=dict,
        description="stock_code → quantity (matches stock_recommendations.recommendation in MongoDB)",
    )
    stock_recommendations: list[RecommendationOutputState] = Field(default_factory=list)
    research_outputs: list[ResearchOutputState] = Field(default_factory=list)
    behaviour_analysis: str | None = None
    error: str | None = None

    def to_api_dict(self) -> dict[str, Any]:
        """HTTP response shape: omits customer_id (kept only on internal models for persistence)."""
        data = self.model_dump(mode="json")
        for row in data.get("stock_recommendations") or []:
            if isinstance(row, dict):
                row.pop("customer_id", None)
        for row in data.get("research_outputs") or []:
            if isinstance(row, dict):
                row.pop("customer_id", None)
        return data


# LLM-parse shapes (validated from model JSON outputs)
class _StockSuggestionLLM(BaseModel):
    stock_code: str
    research: str


class StockResearchAgentLLM(BaseModel):
    suggestions: list[_StockSuggestionLLM] = Field(..., min_length=3, max_length=3)


class BehaviourAnalysisAgentLLM(BaseModel):
    behaviour_analysis: str


class _RecoItemLLM(BaseModel):
    stock_code: str
    recommendation: str
    quantity: int = Field(ge=1)
    time_period: str


class RecommendationAgentLLM(BaseModel):
    recommendations: list[_RecoItemLLM] = Field(..., min_length=3, max_length=3)
