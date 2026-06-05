"""
本地开发服务器：静态文件 + /api/refresh 触发 pipeline
启动方式：python3 server.py
"""

import json
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

BASE_DIR = Path(__file__).parent
PIPELINE_SCRIPT = BASE_DIR / "pipeline" / "run.py"
DAILY_JSON = BASE_DIR / "data" / "daily.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()
_running = False


def _today_data_exists() -> bool:
    """检查 daily.json 是否已包含今天的数据"""
    if not DAILY_JSON.exists():
        return False
    try:
        with open(DAILY_JSON, encoding="utf-8") as f:
            data = json.load(f)
        generated = data.get("date") or data.get("generated_at", "")[:10]
        return generated == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False


@app.post("/api/refresh")
async def refresh(force: bool = Query(default=False)):
    global _running

    # 今日数据已存在且不强制刷新 → 直接返回缓存
    if not force and _today_data_exists():
        logger.info("今日数据已存在，返回缓存")
        return JSONResponse({
            "status": "cached",
            "message": "今日数据已存在，直接读取缓存（点击「强制刷新」可重新抓取）",
        })

    if _running:
        return JSONResponse({"status": "running", "message": "任务正在执行中，请稍候..."}, status_code=409)

    _running = True
    logger.info(f"手动触发 pipeline（force={force}）...")

    try:
        result = subprocess.run(
            [sys.executable, str(PIPELINE_SCRIPT)],
            cwd=str(BASE_DIR / "pipeline"),
            capture_output=True,
            text=True,
            timeout=300,
        )
        success = result.returncode == 0
        log_lines = (result.stdout + result.stderr).strip().splitlines()
        tail = "\n".join(log_lines[-10:])
        logger.info(f"Pipeline 完成，returncode={result.returncode}")
        return JSONResponse({
            "status": "success" if success else "error",
            "message": "数据更新成功" if success else "执行失败，请查看日志",
            "log": tail,
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({"status": "error", "message": "执行超时（5分钟）"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    finally:
        _running = False


@app.get("/api/status")
async def status():
    return {"running": _running, "today_cached": _today_data_exists()}


app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888, reload=False)
