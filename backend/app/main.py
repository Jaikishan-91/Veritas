import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth, worker
from .api import router
from .config import get_settings
from .db import get_sessionmaker

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_sessionmaker()  # create schema
    auth.bootstrap_admin()
    worker.resume_pending()
    yield


app = FastAPI(title="Veritas Document Integrity Analyzer", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH"],
    allow_credentials=True,
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(router)
