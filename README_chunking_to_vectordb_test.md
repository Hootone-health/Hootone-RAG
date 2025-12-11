## Chunking to VectorDB (branch: chunking-to-vectordb-test)

This README summarizes only the work under `notebook/` so another developer can continue.

### What’s inside `notebook/`
- `stage-2.ipynb` — end-to-end semantic chunking of local PDFs using Gemma embeddings, then upsert to Qdrant.
- `docker-compose.yml` — runs Qdrant locally and bind-mounts storage to `notebook/Docker bind mount/` for persistence.
- `embedding-demo.py` — minimal script to call the local Model Runner’s OpenAI-compatible embeddings (`ai/embeddinggemma`).
- `Docker bind mount/` — Qdrant data directory created by the container; keep it mounted to retain collections.

### Prerequisites
- Branch: `chunking-to-vectordb-test`.
- Local Docker available.
- Local Model Runner exposing an OpenAI-compatible endpoint (default: `http://localhost:12434/engines/v1`) with the embedding model `ai/embeddinggemma`.
- PDFs placed at `C:\Users\Admin\Desktop\rag-hootone\data\uploads\PDF` (the notebook also writes cleaned copies to the `cleaned/` subfolder).
- Python deps (if running outside a pre-built env): `langchain`, `langchain-community`, `langchain-experimental`, `langchain-openai`, `openai>=1.50`, `pymupdf`, `qdrant-client`, `langchain-qdrant`.

### How to run Qdrant (from `notebook/`)
1) `docker compose up -d`  
   - Exposes HTTP 6333 (and gRPC 6334).  
   - Persists data to `notebook/Docker bind mount/` per the compose file.
2) Optional health check: `curl http://localhost:6333/health`

### Running the embedding demo
```
cd notebook
python embedding-demo.py
```
Notes:
- Uses `MODEL_RUNNER_BASE_URL` (default `http://localhost:12434/engines/v1`) and `OPENAI_API_KEY` (default `docker`).
- Prints embedding dims and a short preview for two sample strings.

### Notebook flow (`stage-2.ipynb`)
1) **Setup**
   - Uses `MODEL_RUNNER_BASE_URL`, `OPENAI_API_KEY` (default `docker`), and `EMBED_MODEL_NAME="ai/embeddinggemma"`.
   - Points `PDF_DIR` to the uploads folder.
2) **PDF preprocessing**
   - Normalizes Unicode (NFKC), strips control chars, collapses whitespace.
   - Re-emits a cleaned PDF per page using PyMuPDF (`PDFPreprocessor`), written to `data\uploads\PDF\cleaned\`.
3) **Load to LangChain Documents**
   - `PyMuPDFLoader` loads each cleaned PDF to `Document` objects.
   - Fails fast if the directory is missing or empty.
4) **Semantic chunking**
   - `SemanticChunker` (from `langchain_experimental.text_splitter`) with Gemma embeddings.
   - Tunable `BREAKPOINT_PERCENTILE` (default 75): lower -> more/smaller chunks, higher -> fewer/larger.
5) **Stats/preview**
   - Prints chunk count and basic length stats; shows a sample chunk.
6) **Persist to Qdrant**
   - Uses `QdrantVectorStore.from_documents` with collection `rag-hootone`.
   - Defaults: `QDRANT_URL=http://localhost:6333`, no API key unless provided; `prefer_grpc=False` (flip if using 6334 gRPC).
   - Output message confirms upsert count and target URL.
7) **Next steps (notebook notes)**
   - Adjust `BREAKPOINT_PERCENTILE`, or swap in another vector store if desired.

### Key paths and persistence
- Qdrant storage: `notebook/Docker bind mount/` (mounted into the Qdrant container). Do not delete if you want to keep collections.
- Cleaned PDFs: `data\uploads\PDF\cleaned\` (created automatically).
- Collection name: `rag-hootone`.

### Quick start checklist
- [ ] `git switch chunking-to-vectordb-test`
- [ ] `docker compose up -d` inside `notebook/`
- [ ] Ensure Model Runner is up with `ai/embeddinggemma` at `http://localhost:12434/engines/v1`
- [ ] Place PDFs in `data\uploads\PDF`
- [ ] Run `stage-2.ipynb` (or reuse the functions within) to chunk and upsert to Qdrant
