resource "aws_secretsmanager_secret" "config" {
  name = "research-agent/config"
}

resource "aws_secretsmanager_secret_version" "config" {
  secret_id = aws_secretsmanager_secret.config.id
  secret_string = jsonencode({
    # LLM providers (consumed by TensorZero sidecar)
    OPENAI_API_KEY = "REPLACE_ME"
    GROQ_API_KEY   = "REPLACE_ME"

    # Observability
    LANGSMITH_API_KEY = "REPLACE_ME"
    LANGCHAIN_PROJECT = "research-agent"
    LANGSMITH_DATASET = "research-agent-reports"

    # Auth
    API_KEY = var.api_key

    # AWS
    AWS_REGION                = var.aws_region
    BEDROCK_GUARDRAIL_ID      = aws_bedrock_guardrail.main.guardrail_id
    BEDROCK_GUARDRAIL_VERSION = aws_bedrock_guardrail_version.main.version

    # Infrastructure endpoints
    REDIS_URL      = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    TENSORZERO_URL = "http://localhost:3000"
    DATABASE_URL   = "postgresql://dbadmin:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/researchdb"

    # Tunable parameters (all have safe defaults in config.py)
    CACHE_TTL                  = "3600"
    CACHE_SIMILARITY_THRESHOLD = "0.85"
    SESSION_TTL                = "1800"
    SESSION_MAX_MESSAGES       = "5"
    SESSION_CONTENT_TRUNCATE   = "500"
    LTM_DAYS                   = "7"
    LTM_THRESHOLD              = "0.88"
    LTM_DIFF_THRESHOLD         = "0.7"
    LTM_DIFF_LIMIT             = "5"
    IVFFLAT_LISTS              = "100"
    STREAM_KEY                 = "research:jobs"
    CONSUMER_GROUP             = "workers"
    RESULT_TTL                 = "3600"
    AGENT_REPORT_TRUNCATE      = "3000"
    AGENT_MAX_ITERATIONS       = "2"
    EVAL_REPORT_TRUNCATE       = "1500"
    EVAL_COMMENT_TRUNCATE      = "300"
    LLM_MAX_RETRIES            = "3"
    LLM_RETRY_DELAY            = "1.0"
    RATE_LIMIT_REQUESTS        = "10"
    RATE_LIMIT_WINDOW          = "60"
    DB_POOL_MIN                = "2"
    DB_POOL_MAX                = "10"
  })
}
