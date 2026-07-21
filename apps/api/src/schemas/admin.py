from pydantic import BaseModel, Field


class VerifyAdminKeyResponse(BaseModel):
    valid: bool


class ValidateKeyRequest(BaseModel):
    api_key: str = Field(default="", description="API key to validate (falls back to server key if empty)")
    base_url: str = Field(default="", description="Custom API base URL")
    provider: str = Field(..., description="Provider name: 'openai', 'openrouter', or 'gemini'")
    model: str = Field(default="openai/gpt-4o", description="Model name to ping")


class ValidateKeyResponse(BaseModel):
    valid: bool
    error: str | None = None


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="client", pattern="^(admin|client)$")
    expires_in_days: int | None = Field(default=None, ge=1)


class ApiKeyCreatedResponse(BaseModel):
    apiKey: str
    keyId: str
    tenantId: str
    prefix: str
    role: str
    status: str
    expiresAt: str | None = None


class CreateUserRequest(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    userId: str
    tenantId: str
    externalId: str
    displayName: str | None
    isActive: bool
    createdAt: str


class CreatePromptRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(...)
    is_system_prompt: bool = False


class PreviewPromptRequest(BaseModel):
    name: str = "default"
    query: str = Field(default="What is the capital of France?")
    context: str | None = None


class ApplyPresetRequest(BaseModel):
    preset: str
