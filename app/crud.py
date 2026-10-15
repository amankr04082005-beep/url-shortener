import secrets
import string

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Click, Url

ALPHABET = string.ascii_letters + string.digits  # base62
CODE_LENGTH = 6
MAX_RETRIES = 5
RESERVED = {"shorten", "stats", "health", "docs", "openapi.json", "redoc"}


class CodeTakenError(Exception):
    pass


def is_reserved_code(code: str) -> bool:
    return code.lower() in RESERVED


def generate_code(length: int = CODE_LENGTH) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if not is_reserved_code(code):
            return code


def create_url(db: Session, original_url: str, custom_code: str | None = None) -> Url:
    if custom_code:
        if is_reserved_code(custom_code):
            raise CodeTakenError(custom_code)
        url = Url(code=custom_code, original_url=original_url)
        db.add(url)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise CodeTakenError(custom_code)
        db.refresh(url)
        return url

    # Random code: retry on the (rare) collision, the unique index is the source of truth
    for _ in range(MAX_RETRIES):
        url = Url(code=generate_code(), original_url=original_url)
        db.add(url)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(url)
        return url
    raise RuntimeError("Could not generate a unique code")


def get_by_code(db: Session, code: str) -> Url | None:
    return db.scalar(select(Url).where(Url.code == code))


def record_click(db: Session, url: Url, user_agent: str | None) -> None:
    # Atomic increment in SQL (no read-modify-write race between requests)
    db.execute(update(Url).where(Url.id == url.id).values(click_count=Url.click_count + 1))
    db.add(Click(url_id=url.id, user_agent=(user_agent or "")[:255] or None))
    db.commit()


def last_clicked_at(db: Session, url_id: int):
    return db.scalar(select(func.max(Click.clicked_at)).where(Click.url_id == url_id))
