import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from . import crud, models
from .database import Base, engine, get_db
from .schemas import ShortenRequest, ShortenResponse, StatsResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # create tables on startup
    yield


app = FastAPI(title="URL Shortener API", version="1.0.0", lifespan=lifespan)

BASE_URL = (os.getenv("BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:8000").rstrip("/")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten(payload: ShortenRequest, db: Session = Depends(get_db)):
    try:
        url = crud.create_url(db, str(payload.url), payload.custom_code)
    except crud.CodeTakenError:
        raise HTTPException(status_code=409, detail="Custom code is already taken")
    return ShortenResponse(code=url.code, short_url=f"{BASE_URL}/{url.code}", original_url=url.original_url)


# NOTE: declared before "/{code}" so "stats" is not treated as a short code
@app.get("/stats/{code}", response_model=StatsResponse)
def stats(code: str, db: Session = Depends(get_db)):
    url = crud.get_by_code(db, code)
    if url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return StatsResponse(
        code=url.code,
        original_url=url.original_url,
        created_at=url.created_at,
        total_clicks=url.click_count,
        last_clicked_at=crud.last_clicked_at(db, url.id),
    )


@app.get("/{code}")
def redirect(code: str, request: Request, db: Session = Depends(get_db)):
    url = crud.get_by_code(db, code)
    if url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    crud.record_click(db, url, request.headers.get("user-agent"))
    return RedirectResponse(url=url.original_url, status_code=307)