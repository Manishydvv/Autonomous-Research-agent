import redis.asyncio as aioredis
from fastapi import Request, HTTPException
from app.core.config import Config


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis_client


def get_graph(request: Request):
    return request.app.state.graph


async def require_api_key(request: Request) -> None:
    config = get_config(request)
    if not config.api_key:
        return  # auth disabled when no key is configured
    key = request.headers.get("X-API-Key", "")
    if key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

