# FastAPI app entry point
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth

app = FastAPI(title="RAG Hootone API", version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["authentication"])


@app.get("/")
async def root():
    return {"message": "RAG Hootone API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
