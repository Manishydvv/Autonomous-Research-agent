import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import redis.asyncio as aioredis

from app.core.config import Config
from app.core.guardrails import validate_input
from app.services.memory import session_add, session_get
from app.services.queue import push_job, get_result
from app.services.output import generate_pdf, get_report_diff
from app.services.eval import evaluate_report, run_batch_evaluation, fetch_recent_topics
from app.api.dependencies import require_api_key, get_config, get_redis, get_graph

router = APIRouter()

class ResearchRequest(BaseModel):
    topic: str
    session_id: str = ""
    output_format: str = "text"

class BatchEvalRequest(BaseModel):
    topics: list[str] = []

async def _rate_limit(request: Request, config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    client_ip = request.client.host
    key = f"ratelimit:{client_ip}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, config.rate_limit_window)
    if count > config.rate_limit_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

@router.get("/")
async def frontend():
    # In Docker: /app/index.html, locally: <project_root>/index.html
    from pathlib import Path
    # routes.py is in app/api, so index.html is at parent.parent.parent
    local_path = Path(__file__).resolve().parent.parent.parent / "index.html"
    docker_path = Path("/app/index.html")
    html_path = local_path if local_path.exists() else docker_path
    return FileResponse(str(html_path))


@router.get("/health")
async def health(redis_client: aioredis.Redis = Depends(get_redis)):
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": "ok" if redis_ok else "error",
    }


@router.post("/research", dependencies=[Depends(require_api_key), Depends(_rate_limit)])
async def start_research(req: ResearchRequest, config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    ok, reason = await validate_input(config, req.topic)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    session_id = req.session_id or str(uuid.uuid4())
    await session_add(redis_client, config, session_id, "user", req.topic)
    job_id = await push_job(redis_client, config, req.topic, session_id, req.output_format)
    return {"job_id": job_id, "session_id": session_id}


@router.get("/result/{job_id}", dependencies=[Depends(require_api_key)])
async def get_job_result(job_id: str, config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    result = await get_result(redis_client, config, job_id)
    if result is None:
        return {"status": "pending"}
    return result


@router.get("/session/{session_id}", dependencies=[Depends(require_api_key)])
async def get_session(session_id: str, redis_client: aioredis.Redis = Depends(get_redis)):
    messages = await session_get(redis_client, session_id)
    return {"session_id": session_id, "messages": messages}


@router.get("/diff/{topic}", dependencies=[Depends(require_api_key)])
async def report_diff(topic: str, config: Config = Depends(get_config)):
    diff = await get_report_diff(config, topic)
    return {"topic": topic, "diff": diff or "No previous report found."}


@router.get("/result/{job_id}/pdf", dependencies=[Depends(require_api_key)])
async def download_pdf(job_id: str, config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    result = await get_result(redis_client, config, job_id)
    if not result or result.get("status") != "done":
        raise HTTPException(status_code=404, detail="Report not ready")
    pdf_bytes = generate_pdf(result.get("topic", "Report"), result["report"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={job_id}.pdf"},
    )


@router.get("/stats", dependencies=[Depends(require_api_key)])
async def stats(config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    info = await redis_client.info()
    keys = await redis_client.dbsize()
    cache_keys = len([k async for k in redis_client.scan_iter("semantic:*")])
    session_keys = len([k async for k in redis_client.scan_iter("session:*")])
    return {
        "redis": {
            "total_keys": keys,
            "cache_entries": cache_keys,
            "active_sessions": session_keys,
            "memory_used_mb": round(info["used_memory"] / 1024 / 1024, 2),
            "connected_clients": info["connected_clients"],
            "uptime_hours": round(info["uptime_in_seconds"] / 3600, 1),
        },
        "tensorzero_url": config.tensorzero_url,
        "guardrail_id": config.bedrock_guardrail_id,
    }


@router.get("/evaluate/{job_id}", dependencies=[Depends(require_api_key)])
async def evaluate_job(job_id: str, config: Config = Depends(get_config), redis_client: aioredis.Redis = Depends(get_redis)):
    result = await get_result(redis_client, config, job_id)
    if not result or result.get("status") != "done":
        raise HTTPException(status_code=404, detail="Job not done yet")
    scores = await evaluate_report(config, job_id, result["topic"], result["report"])
    return {"job_id": job_id, "topic": result["topic"], "scores": scores}


@router.post("/run-evaluation", dependencies=[Depends(require_api_key)])
async def trigger_batch_evaluation(req: BatchEvalRequest, config: Config = Depends(get_config), graph = Depends(get_graph)):
    topics = req.topics if req.topics else await fetch_recent_topics()
    if not topics:
        raise HTTPException(status_code=400, detail="No topics found. Submit at least one research job first.")
    asyncio.create_task(run_batch_evaluation(config, graph, topics))
    return {"message": "Batch evaluation started in background", "topics": len(topics)}
