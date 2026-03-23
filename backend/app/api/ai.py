import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_optional_user
from app.core.database import get_db
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
from app.services.persist_service import get_video_by_url, record_ai_task
from app.services.subtitle_service import extract_subtitles, get_video_context

logger = logging.getLogger(__name__)
router = APIRouter()


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
    db: AsyncSession = Depends(get_db),
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

        await check_ai_llm_access(user, db, request)

        summary = generate_summary(text, source=source)

        try:
            video = await get_video_by_url(db, req.url)
            await record_ai_task(
                db,
                task_type="summary",
                user_id=user.id if user else None,
                video_id=video.id if video else None,
                status="done",
                result_snapshot=json.dumps(summary, ensure_ascii=False)[:2000],
            )
        except Exception:
            logger.warning("Failed to persist AI task", exc_info=True)

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
    db: AsyncSession = Depends(get_db),
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

        await check_ai_llm_access(user, db, request)

        markdown = generate_mindmap(text, source=source)

        try:
            video = await get_video_by_url(db, req.url)
            await record_ai_task(
                db,
                task_type="mindmap",
                user_id=user.id if user else None,
                video_id=video.id if video else None,
                status="done",
                result_snapshot=markdown[:2000] if markdown else None,
            )
        except Exception:
            logger.warning("Failed to persist AI task", exc_info=True)

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
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    try:
        if not req.texts:
            raise ValueError("没有提供字幕文本")

        redis = get_redis()
        url_hash = hashlib.md5(req.url.encode()).hexdigest()[:12]
        cache_key = f"translate:{url_hash}:{req.target_lang}"

        if redis:
            cached = await redis.get(cache_key)
            if cached:
                return TranslateResponse(
                    translations=json.loads(cached), target_lang=req.target_lang
                )

        await check_ai_llm_access(user, db, request)

        translations = translate_subtitles(req.texts, req.target_lang)

        if redis:
            await redis.set(
                cache_key,
                json.dumps(translations, ensure_ascii=False),
                ex=21600,
            )

        try:
            video = await get_video_by_url(db, req.url)
            await record_ai_task(
                db,
                task_type="translate",
                user_id=user.id if user else None,
                video_id=video.id if video else None,
                status="done",
            )
        except Exception:
            logger.warning("Failed to persist AI task", exc_info=True)

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
    db: AsyncSession = Depends(get_db),
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

        await check_ai_llm_access(user, db, request)

        try:
            video = await get_video_by_url(db, req.url)
            await record_ai_task(
                db,
                task_type="chat",
                user_id=user.id if user else None,
                video_id=video.id if video else None,
                status="done",
            )
        except Exception:
            logger.warning("Failed to persist AI task", exc_info=True)

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
