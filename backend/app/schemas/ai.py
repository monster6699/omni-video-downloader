from typing import Literal

from pydantic import BaseModel


class SubtitleItem(BaseModel):
    start: float
    end: float
    text: str


class SubtitleResponse(BaseModel):
    subtitles: list[SubtitleItem]
    full_text: str
    source: str = "none"


class SummaryResponse(BaseModel):
    summary: str
    keypoints: list[str]
    timeline: list[dict]


class MindMapResponse(BaseModel):
    markdown: str


class AIRequest(BaseModel):
    url: str
    text: str | None = None
    source: str | None = None


class ChatRequest(BaseModel):
    url: str
    question: str
    history: list[dict] = []


class TranslateRequest(BaseModel):
    url: str
    texts: list[str]
    target_lang: str = "zh"


class TranslateResponse(BaseModel):
    translations: list[str]
    target_lang: str


class UsageRulesResponse(BaseModel):
    """Public rules for guide page / clients."""

    anon_ai_daily_limit: int
    registered_default_ai_quota: int
    vip_ai_unlimited: bool = True
    subtitle_public_no_llm_quota: bool = True
    anon_limit_scope: str = "summary, mindmap, translate, chat (per IP, UTC day)"


class AIQuotaStatusResponse(BaseModel):
    """Current LLM AI quota for this request (optional auth + IP)."""

    mode: Literal["anonymous", "registered", "vip"]
    unlimited: bool = False
    remaining: int | None = None
    limit: int | None = None
    used: int | None = None
    display: str
    redis_unavailable: bool = False
