from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field(default="standard")
    isolation_level: str = Field(default="logical")


class TenantListItem(BaseModel):
    tenantId: str
    name: str
    status: str
    tier: str
    createdAt: str


class PaginatedTenantList(BaseModel):
    items: list[TenantListItem]
    total: int
