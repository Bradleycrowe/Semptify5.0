import pytest
from types import SimpleNamespace

from fastapi import HTTPException

from app.routers.overlays import ensure_document_access


@pytest.mark.anyio
async def test_ensure_document_access_allows_matching_document():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            return [
                SimpleNamespace(name="abc123.pdf", is_folder=False),
                SimpleNamespace(name="other.txt", is_folder=False),
            ]

    storage = MockStorage()
    await ensure_document_access(storage, "abc123")


@pytest.mark.anyio
async def test_ensure_document_access_denies_missing_document():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            return [
                SimpleNamespace(name="other.pdf", is_folder=False),
            ]

    storage = MockStorage()

    with pytest.raises(HTTPException) as exc:
        await ensure_document_access(storage, "abc123")

    assert exc.value.status_code == 403


@pytest.mark.anyio
async def test_ensure_document_access_returns_503_on_provider_failure():
    class MockStorage:
        async def list_files(self, folder_path: str, recursive: bool = False):
            raise RuntimeError("provider unavailable")

    storage = MockStorage()

    with pytest.raises(HTTPException) as exc:
        await ensure_document_access(storage, "abc123")

    assert exc.value.status_code == 503
