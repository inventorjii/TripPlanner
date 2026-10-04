# Travel Multi-Agent System — LangGraph

Runnable multi-agent travel planner using LangGraph + FastAPI + PostgreSQL.

Workflow:
User -> Planner -> Research -> [Weather | Flight | Hotel | Traffic] in parallel
-> Itinerary -> Budget -> Critic -> Final (or one bounded revision loop).

The four specialist agents write structured results into shared LangGraph state.
Mock provider tools are included, so no paid API keys are required.

By default, the project is configured to use a local Ollama deployment with the `mistral` model. Set the values in `.env` to match your local instance if it runs on a different host or model name.

## Run

Windows:
```powershell
copy .env.example .env
docker compose up --build
```

Then open http://localhost:8000/docs

Example:
```bash
curl -X POST http://localhost:8000/v1/trips   -H "Authorization: Bearer change-me"   -H "Content-Type: application/json"   -d '{"origin":"Bengaluru","destination":"Goa","start_date":"2026-11-10","end_date":"2026-11-13","travelers":2,"budget":45000}'
```

## Replace mocks with real APIs

Replace:
- app/tools/weather.py
- app/tools/flights.py
- app/tools/hotels.py
- app/tools/traffic.py

Keep their returned schemas and the graph can remain unchanged.

Production hardening:
OIDC/JWT, secrets manager, Redis cache/rate limiting, external API circuit breakers,
OpenTelemetry, LLM cost tracking, prompt/model versioning, managed PostgreSQL,
Kubernetes/Helm, security scanning, load tests and human approval before booking/payment.
