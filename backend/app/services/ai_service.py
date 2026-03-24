import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import AsyncGenerator

import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT_SUBTITLE = """你是一个专业的视频内容分析助手。用户会给你一段视频的字幕/转录文本，请你据此生成结构化的视频总结。

请严格按照以下 JSON 格式返回（不要包含 ```json 标记）：
{
  "summary": "2-3段话的视频概述",
  "keypoints": ["要点1", "要点2", "要点3", ...],
  "timeline": [
    {"time": "00:00", "content": "开场介绍..."},
    {"time": "02:30", "content": "讨论第一个话题..."},
    ...
  ]
}

要求：
- summary 用中文写，简明扼要概括视频核心内容
- keypoints 提取 3-8 个关键要点
- timeline 按视频时间线梳理主要内容节点，时间格式为 MM:SS
- 如果文本较短，timeline 可以少一些"""

SUMMARY_SYSTEM_PROMPT_CONTEXT = """你是一个专业的视频内容分析助手。用户会给你视频的元信息（标题、简介、标签、观众弹幕评论等），请你据此尽力推断并生成结构化的视频总结。

请严格按照以下 JSON 格式返回（不要包含 ```json 标记）：
{
  "summary": "2-3段话的视频概述",
  "keypoints": ["要点1", "要点2", "要点3", ...],
  "timeline": []
}

要求：
- summary 用中文写，根据可用信息概括视频核心内容
- keypoints 提取 3-8 个关键要点
- 因为没有完整字幕，timeline 留空数组即可
- 如果有弹幕评论，从中提取观众关注的要点
- 明确标注这是基于元信息（非完整字幕）的分析"""

MINDMAP_SYSTEM_PROMPT_SUBTITLE = """你是一个专业的视频内容分析助手。用户会给你一段视频的字幕/转录文本，请你据此生成一个 Markdown 格式的思维导图大纲。

要求：
- 使用 Markdown 标题和列表语法（# ## ### - 等）
- 第一级标题是视频主题
- 第二级是主要分支/话题
- 第三级及以下是具体内容点
- 内容简洁，每个节点不超过 15 个字
- 层级不超过 4 层
- 用中文输出

示例：
# 视频主题
## 话题一
- 要点 A
- 要点 B
  - 细节 1
## 话题二
- 要点 C
- 要点 D"""

MINDMAP_SYSTEM_PROMPT_CONTEXT = """你是一个专业的视频内容分析助手。用户会给你视频的元信息（标题、简介、标签、观众弹幕评论等），请你据此推断并生成一个 Markdown 格式的思维导图大纲。

要求：
- 使用 Markdown 标题和列表语法（# ## ### - 等）
- 第一级标题是视频主题
- 第二级是主要分支/话题
- 第三级及以下是具体内容点
- 内容简洁，每个节点不超过 15 个字
- 层级不超过 4 层
- 用中文输出
- 从弹幕评论中提取观众讨论的热点话题"""

QA_SYSTEM_PROMPT = """你是一个专业的视频内容问答助手。以下是视频的相关信息，请根据这些内容回答用户的问题。

视频内容：
{transcript}

要求：
- 基于提供的信息回答，如果信息中没有相关内容，请如实说明
- 用中文回答
- 回答简洁准确"""


TRANSLATE_SYSTEM_PROMPT = """你是一名专业字幕翻译。请将用户给出的字幕文本逐行翻译为{target_lang}。

规则：
- 逐行翻译，保持行数与原文完全一致，不可合并或丢行；凡原文非空，译文也必须非空
- 翻译自然流畅、忠实原意
- 仅返回一个 JSON 字符串数组，不要包含任何说明或 ```json 标记
- 数组长度必须与输入行数相同；输出勿过长导致截断，长句可略压缩用词但必须仍为完整 JSON 数组"""

LANG_NAMES = {
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "es": "Español",
    "de": "Deutsch",
}


def _get_client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("未配置 AI API Key，请在 .env 中设置 OPENAI_API_KEY")
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
    )


def _get_translate_client() -> OpenAI:
    """Longer timeout: subtitle translate uses many small batches; upstream may be slow or reset on huge payloads."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("未配置 AI API Key，请在 .env 中设置 OPENAI_API_KEY")
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        timeout=httpx.Timeout(300.0, connect=45.0),
        max_retries=0,
    )


# Smaller batches + enough max_tokens: avoids output truncation (truncated JSON → padded "" → "missing" lines).
_TRANSLATE_MAX_LINES = 24
_TRANSLATE_MAX_INPUT_CHARS = 7200
_TRANSLATE_PARALLEL_WORKERS = 4


def _iter_subtitle_batches(texts: list[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    batch: list[str] = []
    char_budget = 0
    for t in texts:
        extra = len(t) + 6
        if batch and (
            len(batch) >= _TRANSLATE_MAX_LINES
            or char_budget + extra > _TRANSLATE_MAX_INPUT_CHARS
        ):
            batches.append(batch)
            batch = []
            char_budget = 0
        batch.append(t)
        char_budget += extra
    if batch:
        batches.append(batch)
    return batches


def _parse_translation_response(content: str, batch_len: int) -> list[str]:
    content = content.strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        translations = json.loads(content)
        if not isinstance(translations, list):
            raise ValueError("Expected JSON array")
        translations = [str(x) for x in translations]
    except (json.JSONDecodeError, ValueError):
        logger.warning("Translation returned non-array, splitting by lines")
        translations = [line.strip() for line in content.split("\n") if line.strip()]
    while len(translations) < batch_len:
        translations.append("")
    return translations[:batch_len]


def _translation_covers_batch(sources: list[str], translations: list[str]) -> bool:
    """True if every non-empty source line has a non-empty translation."""
    if len(translations) != len(sources):
        return False
    for s, t in zip(sources, translations):
        if s.strip() and not (t or "").strip():
            return False
    return True


_thread_local = threading.local()


def _thread_translate_client() -> OpenAI:
    """One httpx/OpenAI client per worker thread (not safe for concurrent use on same instance)."""
    c = getattr(_thread_local, "translate_client", None)
    if c is None:
        _thread_local.translate_client = _get_translate_client()
    return _thread_local.translate_client


def _translate_batch_with_retries(batch: list[str], system_prompt: str) -> list[str]:
    """Single batch; retries on connection/timeout and on truncated / short JSON output."""
    client = _thread_translate_client()
    user_msg = json.dumps(batch, ensure_ascii=False)
    cap = settings.TRANSLATE_MAX_OUTPUT_TOKENS
    max_out = min(cap, max(2048, len(batch) * 550))
    last_err: Exception | None = None
    last_parsed: list[str] | None = None
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=max_out,
            )
            choice = response.choices[0]
            raw = choice.message.content
            if not raw:
                raise ValueError("模型返回空内容")
            if getattr(choice, "finish_reason", None) == "length":
                logger.warning(
                    "translate batch len=%s hit max_tokens (finish_reason=length), attempt %s/5",
                    len(batch),
                    attempt + 1,
                )
                last_err = ValueError("输出被长度截断")
                time.sleep(0.6 * (attempt + 1))
                continue
            parsed = _parse_translation_response(raw, len(batch))
            last_parsed = parsed
            if _translation_covers_batch(batch, parsed):
                return parsed
            logger.warning(
                "translate batch len=%s incomplete lines or parse mismatch, attempt %s/5",
                len(batch),
                attempt + 1,
            )
            last_err = ValueError("译文行数或内容与原文不对应")
            time.sleep(0.6 * (attempt + 1))
        except (APIConnectionError, APITimeoutError) as e:
            last_err = e
            logger.warning(
                "translate batch len=%s connection/timeout (attempt %s/5): %s",
                len(batch),
                attempt + 1,
                e,
            )
            time.sleep(1.2 * (attempt + 1))
    if last_parsed is not None:
        logger.error(
            "translate batch len=%s still incomplete after retries, returning best effort",
            len(batch),
        )
        return last_parsed
    if last_err is not None:
        raise last_err
    raise RuntimeError("translate batch failed")


def generate_summary(full_text: str, source: str = "subtitle") -> dict:
    """Generate structured video summary from transcript or context text."""
    if not full_text.strip():
        raise ValueError("文本为空，无法生成总结")

    client = _get_client()

    truncated = full_text[:12000]

    if source == "subtitle":
        system_prompt = SUMMARY_SYSTEM_PROMPT_SUBTITLE
        user_msg = f"请对以下视频字幕文本生成总结：\n\n{truncated}"
    else:
        system_prompt = SUMMARY_SYSTEM_PROMPT_CONTEXT
        user_msg = f"请根据以下视频元信息和弹幕评论生成总结：\n\n{truncated}"

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()

    content = content.removeprefix("```json").removesuffix("```").strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"AI returned non-JSON summary, wrapping: {content[:200]}")
        result = {
            "summary": content,
            "keypoints": [],
            "timeline": [],
        }

    if "summary" not in result:
        result["summary"] = content
    if "keypoints" not in result:
        result["keypoints"] = []
    if "timeline" not in result:
        result["timeline"] = []

    return result


def generate_mindmap(full_text: str, source: str = "subtitle") -> str:
    """Generate Markdown mind map outline from transcript or context text."""
    if not full_text.strip():
        raise ValueError("文本为空，无法生成思维导图")

    client = _get_client()

    truncated = full_text[:12000]

    if source == "subtitle":
        system_prompt = MINDMAP_SYSTEM_PROMPT_SUBTITLE
        user_msg = f"请根据以下视频字幕文本生成思维导图大纲：\n\n{truncated}"
    else:
        system_prompt = MINDMAP_SYSTEM_PROMPT_CONTEXT
        user_msg = f"请根据以下视频元信息和弹幕评论生成思维导图大纲：\n\n{truncated}"

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    markdown = response.choices[0].message.content.strip()
    markdown = markdown.removeprefix("```markdown").removeprefix("```md").removesuffix("```").strip()
    return markdown


def translate_subtitles(texts: list[str], target_lang: str) -> list[str]:
    """Translate subtitle texts line-by-line, preserving count.

    Batched requests + parallel workers (each thread has its own client) to cut wall time;
    batch size stays below thresholds that trigger upstream chunked-read errors.
    """
    if not texts:
        return []

    lang_name = LANG_NAMES.get(target_lang, target_lang)
    system_prompt = TRANSLATE_SYSTEM_PROMPT.format(target_lang=lang_name)
    batches = _iter_subtitle_batches(texts)
    if not batches:
        return []

    all_translations: list[str] = []
    n = len(batches)
    workers = min(_TRANSLATE_PARALLEL_WORKERS, n)

    if workers <= 1:
        for batch in batches:
            all_translations.extend(_translate_batch_with_retries(batch, system_prompt))
        return all_translations

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(_translate_batch_with_retries, batch, system_prompt): idx
            for idx, batch in enumerate(batches)
        }
        chunks: list[list[str] | None] = [None] * n
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            chunks[idx] = fut.result()
        for part in chunks:
            if part is not None:
                all_translations.extend(part)

    return all_translations


async def stream_chat(
    full_text: str,
    question: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream Q&A chat response about video content."""
    if not full_text.strip():
        yield "data: 字幕文本为空，无法进行问答\n\n"
        yield "data: [DONE]\n\n"
        return

    client = _get_client()
    truncated = full_text[:10000]

    system_msg = QA_SYSTEM_PROMPT.format(transcript=truncated)

    messages = [{"role": "system", "content": system_msg}]
    for msg in history[-10:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })
    messages.append({"role": "user", "content": question})

    try:
        stream = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=2000,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield f"data: {json.dumps({'content': delta.content}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.exception("Chat stream error")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
