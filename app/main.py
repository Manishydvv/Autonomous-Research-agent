import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from app.core.config import Config
from app.db.pool import init_pool, close_pool
from app.services.memory import db_migrate
from app.services.agents import build_graph
from app.worker.main import _worker_loop
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

config = Config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize globals for dependency injection
    redis_client = await aioredis.from_url(config.redis_url, decode_responses=True)
    await init_pool(config)
    await db_migrate(config)
    graph = build_graph(config)
    
    app.state.config = config
    app.state.redis_client = redis_client
    app.state.graph = graph

    # Start background worker loop
    worker_task = asyncio.create_task(_worker_loop(redis_client, config, graph))
    
    yield
    
    # Cleanup
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await redis_client.aclose()
    await close_pool()


app = FastAPI(title="Research Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
