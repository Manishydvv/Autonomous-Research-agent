# Autonomous Research Agent

An Autonomous AI Research Agent that researches topics, writes reports, and remembers past knowledge. Built on a scalable, production-grade architecture featuring a multi-agent pipeline, long-term semantic memory, and automated red-teaming.

[👉 **Click here for the full AWS & Terraform Deployment Guide**](./DEPLOYMENT.md)

---

## 🧠 Architecture Overview

This project is built using a modern, domain-driven microservices architecture:

| Component | Technology | Purpose |
|---|---|---|
| **API Backend** | FastAPI + `uv` | Modular REST API that receives topics and serves reports. Highly optimized dependency resolution using `uv`. |
| **Agent Pipeline** | LangGraph | 4-agent state machine workflow: Search → Summarize → Write → Verify. |
| **LLM Gateway** | TensorZero | Intelligent LLM routing — defaults to GPT-4o, falls back to Groq Llama-3 automatically. |
| **Content Safety** | AWS Bedrock Guardrails | Blocks harmful input and filters output automatically. |
| **Session Memory & Cache** | Redis (ElastiCache) | Caches recent semantic queries, maintains short-term session memory, and powers the Celery job queue. |
| **Long-Term Memory** | PostgreSQL + `pgvector` | Converts past research into vector embeddings. Enables hybrid semantic search so the agent can reference its past knowledge. |
| **Observability** | LangSmith | Traces every agent step and uses LLM-as-a-judge to score every report on relevance and hallucination risk. |
| **Automated Security** | PyRIT 0.14.0 | Independent container that runs automated red-team attacks (jailbreaks, XPIA, crescendo) on a weekly schedule. |

---

## 📁 File Structure

The codebase is organized into domain-specific modules:

```text
PROJECT/
├── app/
│   ├── api/              # FastAPI endpoints (routes.py, dependencies.py)
│   ├── core/             # Application configuration and LLM setup
│   ├── db/               # PostgreSQL (pgvector) connection pools
│   ├── services/         # Core logic (agents.py, memory.py, guardrails.py)
│   ├── worker/           # Background job processors
│   └── Dockerfile        # uv-optimized container build
├── pyrit_dashboard/      # Independent PyRIT red-teaming microservice
├── tensorzero/           # LLM Gateway configurations
├── terraform/            # Modular IaC (vpc.tf, ecs.tf, rds.tf, etc.)
├── .github/workflows/    # CI/CD pipelines
├── DEPLOYMENT.md         # AWS Deployment Instructions
└── README.md
```

---

## 🚀 Using the App

### 1. The Frontend UI
Once deployed, open the Load Balancer URL in your browser (e.g., `http://<alb_dns>/`).
1. Enter your API key (it saves locally in your browser).
2. Type a research topic.
3. Choose an output format (Text / PDF / JSON).
4. Click **Start Research**. The UI will poll the backend until the agents finish the report.
5. Click **Show Changes vs Previous** to use `pgvector` to compare the new report against older reports on similar topics!

---

### 2. API Endpoints

All requests require the `X-API-Key` header (if you configured one in AWS Secrets Manager).

**Submit a research job:**
```bash
curl -X POST http://<alb_dns>/research \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"topic": "AI chip market 2025", "session_id": "abc123", "output_format": "text"}'
```
*Returns:* `{"job_id": "...", "session_id": "..."}`

**Poll for result:**
```bash
curl http://<alb_dns>/result/<job_id> -H "X-API-Key: your-key"
```

**Download as PDF:**
```bash
curl http://<alb_dns>/result/<job_id>/pdf -H "X-API-Key: your-key" -o report.pdf
```

**Semantic Search (Long-Term Memory):**
```bash
curl http://<alb_dns>/diff/<topic> -H "X-API-Key: your-key"
```

---

## 🛡️ PyRIT Red Team Dashboard

The security testing service runs on port `8001`.
```
http://<alb_dns>:8001/
```

This dashboard executes 4 types of automated attacks against the Research Agent to ensure the Bedrock Guardrails are holding:

1. **Jailbreak:** Direct attempts to bypass safety instructions.
2. **XPIA (Cross-Prompt Injection):** Hiding malicious instructions inside a standard research topic.
3. **Crescendo:** Escalating from innocent questions to harmful content over multiple turns.
4. **Skeleton Key:** Claiming artificial authority (e.g., "I am the CISO") to bypass restrictions.

Results (BLOCKED or PASSED) are saved in Redis. A scheduled EventBridge task also runs these attacks automatically every Monday at 2:00 AM UTC.
