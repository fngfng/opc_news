"""
数据组装模块：合并抓取结果 + AI 解读，输出 JSON 文件
- data/daily.json        （含每日 AI 总结）
- data/history/YYYY-MM-DD.json
- data/weekly.json       （含每周趋势深度分析）
"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
HISTORY_DIR = DATA_DIR / "history"
MODEL = "deepseek-ai/DeepSeek-V4-Pro"


def _client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("缺少 DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")


def _generate_daily_summary(repos: list[dict]) -> str:
    """用 AI 对今日热门项目生成一段总体解读"""
    if not repos:
        return ""
    try:
        lines = []
        for r in repos[:10]:
            lines.append(f"- {r['owner']}/{r['name']}（{r['language']}，今日+{r.get('stars_today',0)}星）：{r.get('description','')}")
        prompt = (
            "以下是今日 GitHub Trending 前10名项目：\n"
            + "\n".join(lines)
            + "\n\n请用150字左右中文写一段今日热点总结，"
            "指出今天开源社区最关注的方向是什么、有哪些值得关注的亮点项目，语言简洁有洞察力。"
            "直接输出正文，不要标题。"
        )
        resp = _client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=250,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"每日总结生成失败: {e}")
        return ""


def save_daily(repos: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    daily_summary = _generate_daily_summary(repos)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "date": today,
        "period": "daily",
        "daily_summary": daily_summary,
        "repos": repos,
    }

    with open(DATA_DIR / "daily.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("已写入 data/daily.json")

    history_path = HISTORY_DIR / f"{today}.json"
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入 data/history/{today}.json")


def build_weekly() -> None:
    """读取近7天 history，聚合生成 weekly.json（含深度趋势分析）"""
    today = datetime.now().date()
    all_repos: list[dict] = []
    dates_found: list[str] = []

    for delta in range(7):
        date_str = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
        path = HISTORY_DIR / f"{date_str}.json"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        all_repos.extend(data.get("repos", []))
        dates_found.append(date_str)

    if not all_repos:
        logger.warning("无历史数据，跳过生成 weekly.json")
        return

    lang_count: dict[str, int] = {}
    for r in all_repos:
        lang = r.get("language", "Unknown")
        lang_count[lang] = lang_count.get(lang, 0) + 1
    top_languages = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:5]

    topic_count: dict[str, int] = {}
    for r in all_repos:
        for t in r.get("topics", []):
            topic_count[t] = topic_count.get(t, 0) + 1
    trending_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:8]

    appear_count: dict[str, int] = {}
    repo_meta: dict[str, dict] = {}
    for r in all_repos:
        key = f"{r['owner']}/{r['name']}"
        appear_count[key] = appear_count.get(key, 0) + 1
        repo_meta[key] = r
    top_keys = sorted(appear_count, key=lambda k: appear_count[k], reverse=True)[:10]
    top_picks = []
    for key in top_keys:
        r = repo_meta[key].copy()
        r["appear_days"] = appear_count[key]
        top_picks.append(r)

    total_stars_today = sum(r.get("stars_today", 0) for r in all_repos)
    week_start = dates_found[-1] if dates_found else ""
    week_end = dates_found[0] if dates_found else ""
    days_count = len(dates_found)

    insights = _generate_weekly_insights(top_picks, top_languages, trending_topics, days_count)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "week_range": f"{week_start} ~ {week_end}",
        "days_collected": days_count,
        "total_projects": len(set(f"{r['owner']}/{r['name']}" for r in all_repos)),
        "total_stars_today": total_stars_today,
        "top_languages": top_languages,
        "trending_topics": trending_topics,
        "top_picks": top_picks,
        "insights": insights,
    }

    with open(DATA_DIR / "weekly.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("已写入 data/weekly.json")


def _generate_weekly_insights(
    top_picks: list[dict],
    top_languages: list[tuple],
    trending_topics: list[tuple],
    days_count: int,
) -> dict:
    """生成结构化的每周趋势深度分析"""
    try:
        top_names = "\n".join(
            "{n}. {owner}/{name}（上榜{days}天，⭐{stars}）：{desc}".format(
                n=i + 1,
                owner=r["owner"],
                name=r["name"],
                days=r.get("appear_days", 1),
                stars=r.get("stars", 0),
                desc=r.get("description", "")[:50],
            )
            for i, r in enumerate(top_picks[:8])
        )
        langs = "、".join(f"{lang}（{cnt}次）" for lang, cnt in top_languages[:5])
        topics = "、".join(f"{t}（{c}次）" for t, c in trending_topics[:6])

        prompt = f"""以下是过去{days_count}天 GitHub Trending 数据汇总：

【本周 Top 项目】
{top_names}

【语言分布】{langs}
【热门话题】{topics}

请从以下3个维度给出深度趋势分析，每个维度2-3句话，直接输出JSON：
{{
  "hot_direction": "本周最热技术方向分析（AI/安全/工具等哪个方向最强势，为什么）",
  "language_trend": "编程语言趋势分析（哪些语言在崛起，哪些在下降，说明原因）",
  "notable_projects": "值得重点关注的项目及原因（从Top列表中挑2-3个，说明为何值得关注）"
}}"""

        resp = _client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        # 提取 JSON
        import re
        text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > 0:
            data = json.loads(text[start:end])
            if all(k in data for k in ("hot_direction", "language_trend", "notable_projects")):
                return data
    except Exception as e:
        logger.warning(f"weekly insights 生成失败: {e}")

    langs_str = "、".join(lang for lang, _ in top_languages[:3])
    return {
        "hot_direction": f"本周共追踪 {len(top_picks)} 个热门项目，持续关注开源生态动态。",
        "language_trend": f"主要语言：{langs_str}。",
        "notable_projects": "、".join(f"{r['owner']}/{r['name']}" for r in top_picks[:3]),
    }
