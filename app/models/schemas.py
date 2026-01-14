# Pydantic schemas (request/response)
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: UUID
    role: str


class IngestDocumentResponse(BaseModel):
    task_id: str
    status: str  # PENDING or IN_PROGRESS
    message: str