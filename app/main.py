from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models

from .api import auth, memories, map, social, places, discovery, media, profile, chat, collections, reports, admin

# Base.metadata.create_all(bind=engine) # We use alembic instead

app = FastAPI(
    title="Waymark API",
    description="Backend API for Waymark memory discovery app",
    version="1.0.0"
)

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(map.router, prefix="/v1/map", tags=["map"])
app.include_router(memories.router, prefix="/v1/memories", tags=["memories"])
app.include_router(social.router, prefix="/v1", tags=["social"])
app.include_router(places.router, prefix="/v1/places", tags=["places"])
app.include_router(discovery.router, prefix="/v1/discovery", tags=["discovery"])
app.include_router(media.router, prefix="/v1", tags=["media"])
app.include_router(profile.router, prefix="/v1/profile", tags=["profile"])
app.include_router(chat.router, prefix="/v1/conversations", tags=["chat"])
app.include_router(collections.router, prefix="/v1/collections", tags=["collections"])
app.include_router(reports.router, prefix="/v1/reports", tags=["reports"])
app.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

from fastapi.responses import HTMLResponse
import os

@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Waymark UI static file not found"

@app.get("/v1/health")
def health_check(db: Session = Depends(get_db)):
    return {"status": "ok", "db_connected": db is not None}
