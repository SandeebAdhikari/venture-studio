"""Shared fixtures for worker tests."""

import pytest

from app.workers.enqueue import close_arq_pool


@pytest.fixture(autouse=True)
async def reset_arq_pool():
    await close_arq_pool()
    yield
    await close_arq_pool()
