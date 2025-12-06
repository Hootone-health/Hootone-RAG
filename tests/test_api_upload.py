import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, _bucket_level, _bucket_updated_at
from src.services import file_handler


@pytest.fixture(autouse=True)
def reset_rate_limit():
    # Reset leaky bucket state between tests
    from src import api
    from src.api import main

    main._bucket_level = 0.0
    main._bucket_updated_at = main.time.monotonic()
    yield


@pytest.fixture
def temp_paths(tmp_path, monkeypatch):
    meta_dir = tmp_path / "Metadata"
    pdf_dir = tmp_path / "PDF"
    monkeypatch.setattr(file_handler, "METADATA_DIR", meta_dir)
    monkeypatch.setattr(file_handler, "PDF_STORAGE_DIR", pdf_dir)
    yield meta_dir, pdf_dir


@pytest.fixture
def client(monkeypatch, temp_paths):
    # Stub DB sync to avoid real DB dependency
    from src.services import db_manager

    monkeypatch.setattr(db_manager, "sync_metadata_directory_to_db", lambda *_, **__: 1)
    return TestClient(app)


def _upload(client: TestClient, file_name: str, body: bytes, content_type: str = "application/pdf"):
    headers = {
        "x-file-name": file_name,
        "content-type": content_type,
        "content-length": str(len(body)),
    }
    return client.post("/upload/pdf", data=body, headers=headers)


def test_upload_succeeds_and_writes_files(client, temp_paths):
    meta_dir, pdf_dir = temp_paths
    resp = _upload(client, "sample.pdf", b"%PDF-1.4 test")
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "sample.pdf"
    assert "unique_id" in data

    pdf_path = pdf_dir / "sample.pdf"
    meta_path = meta_dir / "sample.pdf.txt"
    assert pdf_path.exists()
    assert meta_path.exists()
    assert b"%PDF-1.4" in pdf_path.read_bytes()
    meta_content = meta_path.read_text(encoding="utf-8")
    assert "file_name=sample.pdf" in meta_content
    assert "storage_path=" in meta_content


def test_duplicate_filename_rejected(client, temp_paths):
    resp1 = _upload(client, "dup.pdf", b"one")
    assert resp1.status_code == 201
    resp2 = _upload(client, "dup.pdf", b"two")
    assert resp2.status_code == 409
    assert resp2.json()["message"] == "File already Exist!"


def test_non_pdf_rejected(client):
    resp = _upload(client, "bad.txt", b"not pdf", content_type="text/plain")
    assert resp.status_code == 415

