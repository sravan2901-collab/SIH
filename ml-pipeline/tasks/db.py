import asyncio
import concurrent.futures
import logging
import os
import sys
import uuid
from pathlib import Path

# Ensure backend is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
for candidate in (backend_dir, Path("/app")):
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

logger = logging.getLogger(__name__)

_db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://lmpc_user:changeme_dev_only@db:5432/lmpc")
if not _db_url.startswith("postgresql+asyncpg://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://")

_engine = create_async_engine(_db_url, poolclass=NullPool)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def _async_update_scan_status(scan_id: str, status: str = "processing"):
    from app.models import Scan

    async with _SessionLocal() as session:
        scan = await session.get(Scan, uuid.UUID(scan_id))
        if scan:
            scan.status = status
            await session.commit()
            logger.info("Scan %s status updated to '%s'", scan_id, status)


def update_scan_status(scan_id: str, status: str = "processing"):
    """Synchronously open a database session and update Scan.status in Postgres."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(lambda: asyncio.run(_async_update_scan_status(scan_id, status))).result()
