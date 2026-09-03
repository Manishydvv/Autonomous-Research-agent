import asyncio
import logging
from app.core.config import Config
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


def _apply_guardrail_sync(config: Config, text: str, source: str) -> dict:
    import boto3
    client = boto3.client("bedrock-runtime", region_name=config.aws_region)
    return client.apply_guardrail(
        guardrailIdentifier=config.bedrock_guardrail_id,
        guardrailVersion=config.bedrock_guardrail_version,
        source=source,
        content=[{"text": {"text": text}}],
    )


async def validate_input(config: Config, text: str) -> tuple[bool, str]:
    if not config.bedrock_guardrail_id:
        logger.debug("Guardrails skipped (no BEDROCK_GUARDRAIL_ID configured)")
        return True, ""
    response = await with_retry(
        lambda: asyncio.to_thread(_apply_guardrail_sync, config, text, "INPUT"),
        max_retries=config.llm_max_retries,
        delay=config.llm_retry_delay,
    )
    if response.get("action") == "GUARDRAIL_INTERVENED":
        return False, "Input blocked by safety guardrail."
    return True, ""


async def validate_output(config: Config, text: str) -> tuple[bool, str]:
    if not config.bedrock_guardrail_id:
        logger.debug("Guardrails skipped (no BEDROCK_GUARDRAIL_ID configured)")
        return True, ""
    response = await with_retry(
        lambda: asyncio.to_thread(_apply_guardrail_sync, config, text, "OUTPUT"),
        max_retries=config.llm_max_retries,
        delay=config.llm_retry_delay,
    )
    if response.get("action") == "GUARDRAIL_INTERVENED":
        return False, "Output blocked by safety guardrail."
    return True, ""

