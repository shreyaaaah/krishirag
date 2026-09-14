"""
KrishiRAG FastAPI Data Models
=============================
Pydantic schemas for request and response validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="Farmer question or advisory query text", example="What is the dose of sulfosulfuron for wheat?")


class SourceInfo(BaseModel):
    file: str = Field(..., description="Source PDF filename")
    page: int = Field(..., description="Page number in PDF")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Grounded LLM-generated answer")
    sources: List[SourceInfo] = Field(default=[], description="List of cited source pages")
    response_time_ms: float = Field(..., description="Total processing time in milliseconds")


class MandiPriceRecord(BaseModel):
    id: int
    state: str
    district: Optional[str] = None
    market: Optional[str] = None
    commodity: str
    variety: Optional[str] = None
    grade: Optional[str] = None
    arrival_date: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    modal_price: Optional[float] = None
    fetched_at: Optional[str] = None


class MandiPriceResponse(BaseModel):
    total: int = Field(..., description="Total matching records found")
    data: List[MandiPriceRecord] = Field(default=[], description="Matching mandi price rows")
