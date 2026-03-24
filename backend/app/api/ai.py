import asyncio
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.auth import get_optional_user
from app.core.database import async_session
from app.core.redis import get_redis
from app.models.user import User
from app.core.config import settings
from app.core.permissions import (
    check_ai_llm_access,
    read_anon_ai_used_today,
    user_has_active_vip,
)
from app.schemas.ai import (
    AIRequest,
    AIQuotaStatusResponse,
    ChatRequest,
    MindMapResponse,
    SubtitleResponse,
    SummaryResponse,
    TranslateRequest,
    TranslateResponse,
    UsageRulesResponse,
)
from app.services.ai_service import (
    generate_mindmap,
    generate_summary,
    stream_chat,
    translate_subtitles,
)
from app.services.persist_service import persist_ai_task_for_url
from app.services.subtitle_service import extract_subtitles, get_video_context

logger = logging.getLogger(__name__)
router = APIRouter()


def _translate_cache_key(url: str, target_lang: str, texts: list[str]) -> str:
    """Include subtitle body fingerprint — URL-only keys caused misalignment when
    line count/splitting changed but Redis still returned an old translation array."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    payload = json.dumps(texts, ensure_ascii=False).encode("utf-8")
    content_hash = hashlib.sha256(payload).hexdigest()[:24]
    return f"translate:v2:{url_hash}:{target_lang}:{content_hash}"


@router.get("/usage-rules", response_model=UsageRulesResponse)
async def api_usage_rules():
    """Public: limits for anonymous vs logged-in (for 使用说明 page)."""
    return UsageRulesResponse(
        anon_ai_daily_limit=settings.ANON_AI_DAILY_LIMIT,
        registered_default_ai_quota=settings.REGISTER_DEFAULT_AI_QUOTA,
    )


@router.get("/quota-status", response_model=AIQuotaStatusResponse)
async def api_ai_quota_status(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    """Current AI (LLM) quota: VIP / registered ai_quota / anonymous daily IP limit."""
    lim = settings.ANON_AI_DAILY_LIMIT

    if user and user_has_active_vip(user):
        return AIQuotaStatusResponse(
            mode="vip",
            unlimited=True,
            remaining=None,
            limit=None,
            used=None,
            display="VIP：AI 分析不限次数",
        )

    if user:
        q = max(0, int(user.ai_quota))
        return AIQuotaStatusResponse(
            mode="registered",
            unlimited=False,
            remaining=q,
            limit=None,
            used=None,
            display=f"免费额度：还可使用 {q} 次（总结/导图/翻译/问答各计 1 次）",
        )

    used, redis_ok = await read_anon_ai_used_today(request)
    if not redis_ok:
        return AIQuotaStatusResponse(
            mode="anonymous",
            unlimited=False,
            remaining=None,
            limit=lim,
            used=None,
            display="未登录：每日有限次 AI；当前额度暂无法显示，请稍后再试或登录后查看",
            redis_unavailable=True,
        )

    u = used or 0
    rem = max(0, lim - u)
    return AIQuotaStatusResponse(
        mode="anonymous",
        unlimited=False,
        remaining=rem,
        limit=lim,
        used=u,
        display=f"未登录：今日还可使用 {rem} / {lim} 次 AI（按 IP，UTC 日）",
    )


@router.post("/subtitle", response_model=SubtitleResponse)
async def api_get_subtitles(req: AIRequest):
    try:
        result = await extract_subtitles(req.url)
        return SubtitleResponse(**result)
    except Exception as e:
        logger.exception("Subtitle extraction failed")
        raise HTTPException(status_code=400, detail=f"字幕提取失败: {str(e)}")


@router.post("/summary", response_model=SummaryResponse)
async def api_get_summary(
    req: AIRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    try:
        if req.text:
            text = req.text
            source = req.source or "subtitle"
        else:
            ctx = await get_video_context(req.url)
            text = ctx["text"]
            source = ctx["source"]
        if not text.strip():
            raise ValueError("该视频暂无可用内容，无法生成总结")

        async with async_session() as db:
            db_user = await db.get(User, user.id) if user else None
            await check_ai_llm_access(db_user, db, request)

        summary = generate_summary(text, source=source)

        await persist_ai_task_for_url(
            url=req.url,
            task_type="summary",
            user_id=user.id if user else None,
            result_snapshot=json.dumps(summary, ensure_ascii=False)[:2000],
        )

        return SummaryResponse(**summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Summary generation failed")
        raise HTTPException(status_code=500, detail=f"总结生成失败: {str(e)}")


@router.post("/mindmap", response_model=MindMapResponse)
async def api_get_mindmap(
    req: AIRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    try:
        if req.text:
            text = req.text
            source = req.source or "subtitle"
        else:
            ctx = await get_video_context(req.url)
            text = ctx["text"]
            source = ctx["source"]
        if not text.strip():
            raise ValueError("该视频暂无可用内容，无法生成思维导图")

        async with async_session() as db:
            db_user = await db.get(User, user.id) if user else None
            await check_ai_llm_access(db_user, db, request)

        markdown = generate_mindmap(text, source=source)

        await persist_ai_task_for_url(
            url=req.url,
            task_type="mindmap",
            user_id=user.id if user else None,
            result_snapshot=markdown[:2000] if markdown else None,
        )

        return MindMapResponse(markdown=markdown)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Mindmap generation failed")
        raise HTTPException(status_code=500, detail=f"思维导图生成失败: {str(e)}")


@router.post("/translate", response_model=TranslateResponse)
async def api_translate_subtitles(
    req: TranslateRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    try:
        if not req.texts:
            raise ValueError("没有提供字幕文本")

        redis = get_redis()
        cache_key = _translate_cache_key(req.url, req.target_lang, req.texts)

        if redis:
            cached = await redis.get(cache_key)
            if cached:
                try:
                    arr = json.loads(cached)
                    if (
                        isinstance(arr, list)
                        and len(arr) == len(req.texts)
                    ):
                        return TranslateResponse(
                            translations=arr, target_lang=req.target_lang
                        )
                    logger.warning(
                        "translate cache ignored: len %s vs request %s",
                        len(arr) if isinstance(arr, list) else type(arr),
                        len(req.texts),
                    )
                except (json.JSONDecodeError, TypeError):
                    logger.warning("translate cache corrupt, ignoring", exc_info=True)

        async with async_session() as db:
            db_user = await db.get(User, user.id) if user else None
            await check_ai_llm_access(db_user, db, request)

        translations = await asyncio.to_thread(
            translate_subtitles, req.texts, req.target_lang
        )

        if redis:
            await redis.set(
                cache_key,
                json.dumps(translations, ensure_ascii=False),
                ex=21600,
            )

        await persist_ai_task_for_url(
            url=req.url,
            task_type="translate",
            user_id=user.id if user else None,
        )

        return TranslateResponse(
            translations=translations, target_lang=req.target_lang
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")


@router.post("/chat")
async def api_chat(
    req: ChatRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    try:
        ctx = await get_video_context(req.url)
        text = ctx["text"]
        if not text.strip():
            async def empty_stream():
                yield f"data: {json.dumps({'content': '该视频暂无可用内容，无法进行问答'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(empty_stream(), media_type="text/event-stream")

        async with async_session() as db:
            db_user = await db.get(User, user.id) if user else None
            await check_ai_llm_access(db_user, db, request)

        await persist_ai_task_for_url(
            url=req.url,
            task_type="chat",
            user_id=user.id if user else None,
        )

        return StreamingResponse(
            stream_chat(text, req.question, req.history),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")
