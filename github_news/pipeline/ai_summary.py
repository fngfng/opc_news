"""
AI 解读模块：调用 DeepSeek API 批量生成中文项目解读
- 每批 5 个，避免超时
- 已有缓存的项目跳过，节省费用
- 单项失败不中断整体流程
"""

from __future__ import annotations

import json
import os
import re
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "你是技术项目分析师。只输出JSON，不要任何解释、不要markdown代码块。"

USER_PROMPT_TEMPLATE = """分析GitHub项目，用中文输出：
项目：{owner}/{name}
描述：{description}
语言：{language}

输出格式（只输出这个JSON，不要其他内容）：
{{"what":"作者做了什么(1句话)","purpose":"解决什么问题(1句话)","scene":"场景1、场景2、场景3"}}"""

FALLBACK_SUMMARY = {
    "what": "开发了一个功能完善的开源工具或框架，解决特定领域的技术问题。",
    "purpose": "为开发者社区提供开箱即用的解决方案，减少重复造轮子。",
    "scene": "通用软件开发、技术原型验证、生产环境部署。",
}


def _get_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("缺少 DEEPSEEK_API_KEY 环境变量")
    return OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")


# 模型有时输出中文键名，统一映射到英文
_KEY_MAP = {
    "作者做了什么": "what", "做了什么": "what",
    "解决什么问题": "purpose", "方便干什么": "purpose", "解决什么": "purpose",
    "应用场景": "scene", "场景": "scene",
}


def _normalize(data: dict) -> dict:
    """将中文键名转为英文，scene 若为列表则转顿号字符串"""
    result = {}
    for k, v in data.items():
        key = _KEY_MAP.get(k, k)
        if key == "scene" and isinstance(v, list):
            v = "、".join(str(i) for i in v)
        result[key] = str(v).strip()
    return result


def _try_fix_json(text: str) -> str:
    """修复常见的 JSON 问题"""
    text = text.strip()
    # 截取到第一个 { 开始
    start = text.find("{")
    if start > 0:
        text = text[start:]
    # 去除控制字符（保留换行/制表符）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # 去除角色注入："user\n" / "assistant\n" 混入值中
    text = re.sub(r'\buser\s*\n', "", text)
    text = re.sub(r'\bassistant\s*\n', "", text)
    # 修复 ",", 模式（逗号被引号包住）→ ","
    text = re.sub(r'",\s*",', '",', text)
    # 去除 键值对末尾多余逗号（,} 或 ,]）
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # 截断修复：去掉最后一个不完整的键值对，补 }
    if text.count("{") > text.count("}"):
        text = re.sub(r',\s*"[^"]*"\s*:\s*"[^"]*$', "", text)
        text = re.sub(r',\s*"[^"]*"\s*:\s*$', "", text)
        text = text.rstrip(",").rstrip() + "}"
    return text


def _extract_json(text: str) -> dict:
    """从模型输出中提取 JSON，兼容各种格式问题"""
    blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
    candidates = blocks if blocks else [text]

    for raw in reversed(candidates):
        raw = _try_fix_json(raw)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            continue
        try:
            data = json.loads(raw[start:end])
            data = _normalize(data)
            if all(k in data for k in ("what", "purpose", "scene")):
                return data
        except json.JSONDecodeError:
            continue

    raise ValueError(f"无法解析: {text[:150]}")


def _generate_one(client: OpenAI, repo: dict) -> dict:
    user_msg = USER_PROMPT_TEMPLATE.format(
        owner=repo["owner"],
        name=repo["name"],
        description=repo.get("description", "暂无描述") or "暂无描述",
        language=repo.get("language", "Unknown"),
    )
    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=200,
    )
    text = response.choices[0].message.content.strip()
    return _extract_json(text)


def generate_summaries(repos: list, cache: dict | None = None) -> list:
    """
    为 repo 列表生成 AI 解读，返回带 summary 字段的新列表。
    cache: {"{owner}/{name}": summary_dict} 已有缓存直接复用
    """
    cache = cache or {}
    client = _get_client()
    result = []

    for i, repo in enumerate(repos):
        key = f"{repo['owner']}/{repo['name']}"

        if key in cache:
            logger.info(f"[{i+1}/{len(repos)}] 缓存命中：{key}")
            repo["summary"] = cache[key]
            result.append(repo)
            continue

        try:
            logger.info(f"[{i+1}/{len(repos)}] 生成解读：{key}")
            summary = _generate_one(client, repo)
            repo["summary"] = summary
        except Exception as e:
            # 失败后重试一次
            try:
                logger.warning(f"[{i+1}/{len(repos)}] 首次失败，重试：{e}")
                summary = _generate_one(client, repo)
                repo["summary"] = summary
            except Exception as e2:
                logger.warning(f"[{i+1}/{len(repos)}] 重试失败（{e2}），使用兜底文案")
                repo["summary"] = FALLBACK_SUMMARY.copy()

        result.append(repo)

    return result


def load_summary_cache(history_dir: str) -> dict:
    """从近 7 天 history 文件中提取已生成的 summary，避免重复调用 AI"""
    import os
    from pathlib import Path
    from datetime import datetime, timedelta

    cache = {}
    today = datetime.now().date()

    for delta in range(1, 8):
        date_str = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        path = Path(history_dir) / f"{date_str}.json"
        if not path.exists():
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            for repo in data.get("repos", []):
                key = f"{repo['owner']}/{repo['name']}"
                if key not in cache and "summary" in repo:
                    cache[key] = repo["summary"]
        except Exception:
            continue

    logger.info(f"从历史文件加载 {len(cache)} 条 summary 缓存")
    return cache
