"""
数据抓取模块：双源容灾
主源：github-trending-api.de
兜底：爬取 github.com/trending
"""

import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

THIRD_PARTY_API = "https://github-trending-api.de/repositories"
GITHUB_TRENDING_URL = "https://github.com/trending"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_from_api(since: str = "daily", language: str = "") -> list[dict]:
    """从 github-trending-api.de 获取数据"""
    params = {"since": since}
    if language:
        params["language"] = language

    resp = requests.get(THIRD_PARTY_API, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    repos = resp.json()

    result = []
    for i, r in enumerate(repos[:25]):
        result.append({
            "rank": i + 1,
            "name": r.get("name", ""),
            "owner": r.get("author", ""),
            "url": r.get("url", ""),
            "description": r.get("description") or "",
            "stars": r.get("stars", 0),
            "forks": r.get("forks", 0),
            "stars_today": r.get("currentPeriodStars", 0),
            "language": r.get("language") or "Unknown",
            "topics": r.get("builtBy", []),
        })
    return result


def fetch_from_scraper(since: str = "daily") -> list[dict]:
    """爬取 github.com/trending 作为兜底"""
    url = f"{GITHUB_TRENDING_URL}?since={since}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")

    result = []
    for i, article in enumerate(articles[:25]):
        try:
            title = article.select_one("h2 a")
            if not title:
                continue
            href = title.get("href", "").strip("/")
            parts = href.split("/")
            if len(parts) < 2:
                continue
            owner, name = parts[0], parts[1]

            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            stars_el = article.select("a.Link--muted")
            stars = _parse_number(stars_el[0].get_text(strip=True)) if stars_el else 0
            forks = _parse_number(stars_el[1].get_text(strip=True)) if len(stars_el) > 1 else 0

            stars_today_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_today_text = stars_today_el.get_text(strip=True) if stars_today_el else "0"
            stars_today = _parse_number(stars_today_text)

            lang_el = article.select_one("span[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else "Unknown"

            result.append({
                "rank": i + 1,
                "name": name,
                "owner": owner,
                "url": f"https://github.com/{owner}/{name}",
                "description": description,
                "stars": stars,
                "forks": forks,
                "stars_today": stars_today,
                "language": language,
                "topics": [],
            })
        except Exception as e:
            logger.warning(f"解析第 {i+1} 条时出错: {e}")
            continue

    return result


def _parse_number(text: str) -> int:
    text = text.replace(",", "").strip()
    try:
        if "k" in text.lower():
            return int(float(text.lower().replace("k", "")) * 1000)
        return int("".join(filter(str.isdigit, text)) or 0)
    except ValueError:
        return 0


def fetch_trending(since: str = "daily") -> list[dict]:
    """主入口：优先第三方 API，失败降级爬虫"""
    try:
        logger.info("尝试从第三方 API 获取 Trending 数据...")
        repos = fetch_from_api(since=since)
        if repos:
            logger.info(f"第三方 API 成功，获取 {len(repos)} 个项目")
            return repos
        raise ValueError("返回数据为空")
    except Exception as e:
        logger.warning(f"第三方 API 失败（{e}），降级到爬虫...")
        repos = fetch_from_scraper(since=since)
        logger.info(f"爬虫成功，获取 {len(repos)} 个项目")
        return repos
