"""
Pipeline 入口：串联 fetch → ai_summary → build_data
使用方式：
  python pipeline/run.py
  python pipeline/run.py --since weekly   # 获取本周热门
  python pipeline/run.py --skip-ai        # 跳过 AI 解读（调试用）
"""

import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).parent.parent / ".env")

from fetch_trending import fetch_trending
from ai_summary import generate_summaries, load_summary_cache
from build_data import save_daily, build_weekly, fetch_star_charts, HISTORY_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending 数据管道")
    parser.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"])
    parser.add_argument("--skip-ai", action="store_true", help="跳过 AI 解读（调试用）")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info(f"开始执行数据管道 since={args.since}")
    logger.info("=" * 50)

    # Step 1: 抓取 Trending 数据
    try:
        repos = fetch_trending(since=args.since)
        logger.info(f"Step 1 完成：获取 {len(repos)} 个项目")
    except Exception as e:
        logger.error(f"Step 1 失败，数据抓取异常: {e}")
        sys.exit(1)

    # Step 2: AI 批量解读
    if args.skip_ai:
        logger.info("Step 2 跳过（--skip-ai）")
        for repo in repos:
            repo["summary"] = {
                "what": "（AI 解读已跳过）",
                "purpose": "（AI 解读已跳过）",
                "scene": "（AI 解读已跳过）",
            }
    else:
        try:
            cache = load_summary_cache(str(HISTORY_DIR))
            repos = generate_summaries(repos, cache=cache)
            logger.info(f"Step 2 完成：AI 解读生成完毕")
        except Exception as e:
            logger.error(f"Step 2 失败，AI 解读异常: {e}")
            sys.exit(1)

    # Step 3: 写入 JSON 文件
    try:
        save_daily(repos)
        build_weekly()
        logger.info("Step 3 完成：数据文件已写入")
    except Exception as e:
        logger.error(f"Step 3 失败，文件写入异常: {e}")
        sys.exit(1)

    # Step 4: 下载星标趋势图（失败不中断）
    try:
        fetch_star_charts(repos)
        logger.info("Step 4 完成：星标趋势图已缓存")
    except Exception as e:
        logger.warning(f"Step 4 失败（{e}），不影响主流程")

    logger.info("=" * 50)
    logger.info("Pipeline 执行成功 ✓")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
