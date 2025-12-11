RAG Hootone
============
FastAPI service for rate-limited, streamed PDF uploads that writes PDF + metadata to disk and syncs metadata to PostgreSQL. A companion notebook pipeline chunks cleaned PDFs into vectors and pushes them to Qdrant.

Project Layout
- `src/api/main.py` – FastAPI app, leaky-bucket rate limiting, endpoints.
- `src/services/file_handler.py` – streamed PDF validation + storage + metadata files.
- `src/services/db_manager.py` – reads metadata files and inserts into Postgres.
- `src/models/api_models.py` – Pydantic models, rate-limit config, constants (paths/limits).
- `notebook/` – Qdrant + embeddings pipeline (`stage-2.ipynb`, `embedding-demo.py`, `docker-compose.yml`).
- `data/uploads/PDF/` – uploaded PDFs (raw). `data/uploads/Metadata/` – metadata `.txt`.
- `tests/test_api_upload.py` – API happy-path and validation tests.
- `docker-compose.yaml` – Postgres + PgAdmin for the API service (root).
- `requirements.txt` / `pyproject.toml` – Python deps (FastAPI, psycopg3, LangChain, etc.).

Prerequisites
- Python 3.13+
- Docker + Docker Compose
- `uv` (or pip) for dependency management
- Windows paths are hard-coded in `src/models/api_models.py` for storage directories:
  - PDFs: `C:\Users\Admin\Desktop\rag-hootone\data\uploads\PDF`
  - Metadata: `C:\Users\Admin\Desktop\rag-hootone\data\uploads\Metadata`

Setup (API)
1) Install deps  
   - `uv sync` (recommended) or `pip install -r requirements.txt`
2) Environment (create `.env` in repo root)
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=app_db
   DB_USER=admin
   DB_PASSWORD=admin
   POSTGRES_DB=app_db
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=admin
   POSTGRES_PORT=5432
   PGADMIN_DEFAULT_EMAIL=admin@example.com
   PGADMIN_DEFAULT_PASSWORD=admin
   PGADMIN_PORT=5050
   ```
3) Start Postgres (+ optional PgAdmin)
   - `docker-compose up -d`
4) Create table (run once in Postgres)
   ```
   CREATE TABLE IF NOT EXISTS metadata (
     unique_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     file_name VARCHAR(255) NOT NULL,
     storage_path TEXT NOT NULL
   );
   CREATE UNIQUE INDEX IF NOT EXISTS idx_metadata_unique_id ON metadata(unique_id);
   ```
5) Run API
   - `uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`
   - Docs: http://localhost:8000/docs

API Cheatsheet
- Health: `GET /health`
- Rate limit probe: `GET /rate-limit` (also consumes a token)
- Upload PDF (streamed, no UploadFile):
  - Headers: `x-file-name: <name>.pdf`, `content-type: application/pdf`, `content-length` (recommended)
  - Constraints: PDF only, max 100 MB, duplicate filenames rejected (case-sensitive), magic-bytes check for `%PDF`
  - Example:
    ```
    curl -X POST http://localhost:8000/upload/pdf \
      -H "x-file-name: sample.pdf" \
      -H "content-type: application/pdf" \
      --data-binary @sample.pdf
    ```
- On success: stores file at `data/uploads/PDF/<name>.pdf`, writes metadata `.txt` alongside, then attempts DB sync.
- Rate limiting: leaky bucket (capacity=2, leak_rate=0.016 req/sec). Tune in `LeakyBucketConfig` (`src/models/api_models.py`).

Storage Notes
- Directories auto-created on first upload.
- Metadata files are key/value per line and are the single source for DB sync (`sync_metadata_directory_to_db`).

Testing
- Unit/API tests: `pytest`
- Tests stub DB sync and use temp dirs; no Postgres needed to run them.

Notebook / Vector Pipeline (Qdrant)
- See `README_chunking_to_vectordb_test.md` for the notebook branch flow.
- Quick start (from `notebook/`):
  - `docker compose up -d` (Qdrant with bind mount at `notebook/Docker bind mount/`)
  - Ensure PDFs exist at `data/uploads/PDF` (cleaned copies written to `data/uploads/PDF/cleaned/`)
  - Run `stage-2.ipynb` to preprocess, chunk, and upsert to Qdrant collection `rag-hootone`
  - `embedding-demo.py` calls the Model Runner’s OpenAI-compatible embeddings (`ai/embeddinggemma`).

Developer Tips
- Keep Windows paths in `api_models.py` aligned with your environment if relocating the repo.
- If you change storage locations, also update any notebooks expecting `data/uploads/…`.
- For DB connection overrides, use env vars (`DB_HOST`, etc.) rather than editing code.
- When touching upload logic, add/extend tests in `tests/test_api_upload.py` to cover validation paths.

Contribution Checklist
- [ ] `uv sync` (or pip install) and `pytest`
- [ ] `docker-compose up -d` for Postgres when testing DB sync
- [ ] Update docs/readme if you change endpoints, limits, or paths
- [ ] Add/adjust tests for new validation or storage behavior
