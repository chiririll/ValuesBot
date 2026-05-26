from __future__ import annotations

from pathlib import Path

import pytest

from bot.core.values import Catalog, load_catalog
from bot.db.sessions_repo import SessionsRepository
from bot.services.session_service import SessionService

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALUES_FIXTURE = FIXTURES_DIR / "values.json"


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog(VALUES_FIXTURE)


@pytest.fixture
async def repo(tmp_path: Path) -> SessionsRepository:
    repository = SessionsRepository(tmp_path / "test.db")
    await repository.init()
    yield repository
    await repository.close()


@pytest.fixture
async def service(repo: SessionsRepository, catalog: Catalog) -> SessionService:
    return SessionService(repo, catalog)
