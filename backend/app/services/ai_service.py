import json
import logging
from typing import AsyncGenerator

from openai import OpenAI

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
- 逐行翻译，保持行数与原文完全一致
- 翻译自然流畅、忠实原意
- 仅返回一个 JSON 字符串数组，不要包含任何说明或 ```json 标记
- 数组长度必须与输入行数相同"""

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
    """Translate subtitle texts line-by-line, preserving count."""
    if not texts:
        return []

    client = _get_client()
    lang_name = LANG_NAMES.get(target_lang, target_lang)
    system_prompt = TRANSLATE_SYSTEM_PROMPT.format(target_lang=lang_name)

    batch_size = 200
    all_translations: list[str] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        user_msg = json.dumps(batch, ensure_ascii=False)

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=8000,
        )

        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()

        try:
            translations = json.loads(content)
            if not isinstance(translations, list):
                raise ValueError("Expected JSON array")
            translations = [str(t) for t in translations]
        except (json.JSONDecodeError, ValueError):
            logger.warning("Translation returned non-array, splitting by lines")
            translations = [line.strip() for line in content.strip().split("\n") if line.strip()]

        while len(translations) < len(batch):
            translations.append("")
        translations = translations[: len(batch)]

        all_translations.extend(translations)

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
