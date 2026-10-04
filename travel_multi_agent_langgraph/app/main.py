import sys
import asyncio

# # ✅ Fix: set event loop policy before importing Psycopg-related modules
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_settings
    from app.workflow import build_workflow
    from app.schemas import TripRequest, TripResponse
else:
    from .config import get_settings
    from .workflow import build_workflow
    from .schemas import TripRequest, TripResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel-agent")

REQUESTS = Counter("travel_requests_total", "Travel requests", ["status"])
LATENCY = Histogram("travel_request_duration_seconds", "Travel request duration")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("lifespan: initializing app and workflow")
    try:
        cm = AsyncPostgresSaver.from_conn_string(get_settings().database_url)
        checkpointer = await cm.__aenter__()
        await checkpointer.setup()
        app.state.workflow = build_workflow(checkpointer)
        app.state.checkpointer_cm = cm
        logger.info("lifespan: Postgres workflow checkpointer initialized")
        yield
        await cm.__aexit__(None, None, None)
    except Exception as exc:
        logger.warning("Postgres checkpointer unavailable; starting app without persistent workflow state: %s", exc)
        app.state.workflow = build_workflow()
        app.state.checkpointer_cm = None
        logger.info("lifespan: workflow started without Postgres persistence")
        yield

app = FastAPI(title="Travel Multi-Agent System", version="1.0.0", lifespan=lifespan)


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        LATENCY.observe(time.perf_counter() - start)

def authorize(authorization: str | None):
    if authorization != f"Bearer {get_settings().api_key}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
async def root():
    return RedirectResponse(url="/ui")

@app.get("/ui")
async def ui_page():
    return FileResponse(Path(__file__).resolve().with_name("ui.html"))

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready(request: Request):
    if not hasattr(request.app.state, "workflow"):
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")

@app.post("/v1/trips", response_model=TripResponse)
async def create_trip(
    payload: TripRequest,
    request: Request,
    authorization: str | None = Header(default=None),
):
    logger.info("create_trip: request received for %s -> %s", payload.origin, payload.destination)
    authorize(authorization)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    try:
        logger.info("create_trip: invoking workflow with thread_id=%s", thread_id)
        result = await request.app.state.workflow.ainvoke(
            {"request": payload.model_dump()},
            config=config,
        )
        logger.info("create_trip: workflow completed for thread_id=%s", thread_id)
        REQUESTS.labels(status="success").inc()
        return TripResponse(thread_id=thread_id, status="completed", result=result["final_result"])
    except Exception:
        REQUESTS.labels(status="error").inc()
        logger.exception("create_trip: Travel workflow failed")
        raise HTTPException(status_code=500, detail="Travel workflow failed")


if __name__ == "__main__":
    main()

