import asyncio
import uuid
import logging
import traceback
from datetime import datetime
import redis.asyncio as aioredis

from app.core.config import Config
from app.services.cache import cache_get, cache_set
from app.core.guardrails import validate_output
from app.services.memory import session_add, session_get, ltm_search, ltm_search_related, ltm_store, ltm_diff
from app.services.queue import set_result, ensure_group, consume_jobs, ack_job
from app.services.agents import ResearchState
from app.services.output import generate_pdf, generate_json_report
from app.services.eval import evaluate_report

logger = logging.getLogger(__name__)

async def _worker_loop(redis_client: aioredis.Redis, config: Config, graph):
    await ensure_group(redis_client, config)
    while True:
        try:
            jobs = await consume_jobs(redis_client, config)
            for job in jobs:
                asyncio.create_task(_process_job(job["data"], job["msg_id"], redis_client, config, graph))
        except Exception:
            await asyncio.sleep(1)


async def _process_job(data: dict, msg_id: str, redis_client: aioredis.Redis, config: Config, graph):
    job_id = data["job_id"]
    topic = data["topic"]
    session_id = data["session_id"]
    output_format = data.get("output_format", "text")
    log = logging.getLogger(f"job.{job_id[:8]}")
    try:
        log.info(f"Starting job for topic: {topic}")

        # Fetch session history before any branch — agent always receives it
        session_history = await session_get(redis_client, session_id)

        cached = await cache_get(redis_client, config, topic)
        if cached:
            log.info("Cache hit")
            report_text = cached
            await ltm_store(config, topic, report_text, str(uuid.uuid4()))
        else:
            ltm_hit = await ltm_search(config, topic)
            if ltm_hit:
                log.info("LTM hit")
                report_text = ltm_hit["report"]
                await ltm_store(config, topic, report_text, str(uuid.uuid4()))
            else:
                log.info("Running multi-agent pipeline")
                # Find a related (not identical) previous report for the writer to reference
                ltm_context = await ltm_search_related(config, topic) or ""
                if ltm_context:
                    log.info("Found related LTM context for writer agent")
                state = ResearchState(
                    topic=topic,
                    session_id=session_id,
                    session_history=session_history,  # agent is now context-aware
                    ltm_context=ltm_context,           # writer builds on prior research
                    search_results=[],
                    summaries=[],
                    report="",
                    verified=False,
                    error="",
                    iterations=0,
                )
                final_state = await graph.ainvoke(state)
                report_text = final_state["report"]
                ok, reason = await validate_output(config, report_text)
                if not ok:
                    await set_result(redis_client, config, job_id, {"status": "blocked", "error": reason})
                    await ack_job(redis_client, config, msg_id)
                    return
                await cache_set(redis_client, config, topic, report_text)
                await ltm_store(config, topic, report_text, str(uuid.uuid4()))

        await session_add(redis_client, config, session_id, "assistant", report_text[:config.session_content_truncate])
        diff = await ltm_diff(config, topic)
        result: dict = {"status": "done", "topic": topic, "report": report_text, "diff": diff}

        # Per-query evaluation runs automatically on every job
        asyncio.create_task(evaluate_report(config, job_id, topic, report_text))

        if output_format == "pdf":
            pdf_bytes = generate_pdf(topic, report_text)
            result["pdf_base64"] = __import__("base64").b64encode(pdf_bytes).decode()
        elif output_format == "json":
            result["structured"] = generate_json_report(topic, report_text, job_id, datetime.utcnow())

        await set_result(redis_client, config, job_id, result)
        log.info("Job completed successfully")
    except Exception as e:
        log.error(f"Job failed: {traceback.format_exc()}")
        await set_result(redis_client, config, job_id, {"status": "error", "error": str(e)})
    finally:
        await ack_job(redis_client, config, msg_id)
