"""Tenant management routes."""
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["Tenants"])
