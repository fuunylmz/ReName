from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_llm import router as llm_router
from app.api.routes_media import router as media_router
from app.api.routes_settings import router as settings_router
from app.core.config import get_settings
from app.core.database import create_db_and_tables
from app.models import media as media_models

_ = media_models

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(settings_router, prefix="/api")
app.include_router(llm_router, prefix="/api")
app.include_router(media_router, prefix="/api")
