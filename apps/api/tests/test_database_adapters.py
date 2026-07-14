import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.inference_repository import SqlChatSessionRepository
from src.adapters.database.models import ChatMessageDb, TenantConfigDb
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.domain.abstractions.inference import ChatMessage


@pytest.mark.asyncio
@patch("src.adapters.database.tenant_repository.tenant_session", autospec=True)
async def test_tenant_registry_get_config_sets_rls(mock_session_ctx) -> None:
    tenant_id = str(uuid.uuid4())
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_db_config = TenantConfigDb(
        tenant_id=uuid.UUID(tenant_id),
        active_model="model-1",
        temperature=0.1,
        chunk_size=100,
        chunk_overlap=10,
        system_prompt_template="prompt-1",
    )

    # Set up mock execute return value
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_db_config
    mock_db_session.execute.return_value = mock_result

    registry = SqlTenantRegistry()
    config = await registry.get_config(tenant_id)

    # Assert correct domain mapping
    assert config is not None
    assert config.active_model == "model-1"

    # Assert transaction was initialized with tenant_id context matching parameter
    mock_session_ctx.assert_called_once_with(tenant_id=tenant_id)


@pytest.mark.asyncio
@patch("src.adapters.database.identity_repository.tenant_session", autospec=True)
async def test_identity_provider_validate_token_bypasses_rls(mock_session_ctx) -> None:
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    # Set return value to mock missing key (will raise exception but triggers target calls)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    provider = SqlIdentityProvider()
    with pytest.raises(Exception):
        await provider.validate_token("ret_live_token.secretpart")

    # Assert context initialized bypassing RLS limits to enable identity validation checks
    mock_session_ctx.assert_called_once_with(bypass_rls=True)


@pytest.mark.asyncio
@patch("src.adapters.database.inference_repository.tenant_session", autospec=True)
async def test_chat_message_repository_scopes_writes_to_tenant(mock_session_ctx) -> None:
    tenant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    mock_db_session = MagicMock()
    mock_db_session.flush = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    repository = SqlChatSessionRepository()
    await repository.add_message(
        tenant_id,
        session_id,
        ChatMessage(role="user", content="tenant-safe message"),
    )

    mock_session_ctx.assert_called_once_with(tenant_id=tenant_id)
    stored = mock_db_session.add.call_args.args[0]
    assert isinstance(stored, ChatMessageDb)
    assert stored.tenant_id == uuid.UUID(tenant_id)


@pytest.mark.asyncio
@patch("src.adapters.database.inference_repository.tenant_session", autospec=True)
async def test_chat_message_repository_scopes_reads_to_tenant(mock_session_ctx) -> None:
    tenant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    mock_db_session = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    repository = SqlChatSessionRepository()
    assert await repository.get_messages(tenant_id, session_id) == []

    mock_session_ctx.assert_called_once_with(tenant_id=tenant_id)
    statement = mock_db_session.execute.call_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "chat_messages.tenant_id" in compiled
    assert "chat_messages.session_id" in compiled
