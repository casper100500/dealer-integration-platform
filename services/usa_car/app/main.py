"""HTTP API for the file-backed USA Car service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator

from fastapi import (
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.config import Settings
from app.inventory import FeedValidationError, InventoryStore
from app.models import (
    FeedStatusResponse,
    InventoryResponse,
    TokenRequest,
    TokenResponse,
)


def create_app(
    settings: Settings | None = None,
    store: InventoryStore | None = None,
) -> FastAPI:
    """Create a configured USA Car FastAPI application."""
    active_settings = settings or Settings.from_environment()
    active_store = store or InventoryStore(active_settings.inventory_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Load the persisted feed before accepting requests."""
        del application
        active_store.load()
        yield

    service = FastAPI(
        title="USA Car Inventory Service",
        version="1.0.0",
        description=(
            "A file-backed vehicle provider used to demonstrate "
            "service-to-service inventory integration."
        ),
        docs_url="/swagger",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @service.get("/health/", tags=["operations"])
    async def health() -> dict[str, str]:
        """Report that the USA Car process is ready."""
        return {"status": "ok"}

    @service.post(
        "/v1/auth/token/",
        response_model=TokenResponse,
        tags=["dealer API"],
    )
    async def create_token(credentials: TokenRequest) -> TokenResponse:
        """Exchange configured dealer credentials for an access token."""
        if (
            credentials.login != active_settings.api_login
            or credentials.password != active_settings.api_password
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid USA Car credentials.",
            )
        return TokenResponse(access_token=active_settings.access_token)

    @service.get(
        "/v1/inventory/",
        response_model=InventoryResponse,
        tags=["dealer API"],
    )
    async def inventory(
        authorization: Annotated[str | None, Header()] = None,
        cursor: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> InventoryResponse:
        """Return one authenticated page of available inventory."""
        _require_bearer_token(
            authorization,
            active_settings.access_token,
        )
        try:
            records, next_cursor = active_store.inventory_page(
                cursor,
                limit,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        return InventoryResponse(
            inventory=records,
            next_cursor=next_cursor,
        )

    @service.post(
        "/internal/v1/feed/",
        response_model=FeedStatusResponse,
        tags=["supplier feed"],
    )
    async def upload_feed(
        feed: Annotated[UploadFile, File(description="Supplier CSV feed")],
        x_admin_key: Annotated[str | None, Header()] = None,
    ) -> FeedStatusResponse:
        """Validate, persist, and activate a complete supplier feed."""
        _require_admin_key(x_admin_key, active_settings.admin_key)
        data = await feed.read()
        try:
            return active_store.replace(feed.filename or "feed.csv", data)
        except FeedValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=error.errors,
            ) from error

    @service.get(
        "/internal/v1/feed/status/",
        response_model=FeedStatusResponse,
        tags=["supplier feed"],
    )
    async def feed_status(
        x_admin_key: Annotated[str | None, Header()] = None,
    ) -> FeedStatusResponse:
        """Return metadata for the active supplier feed."""
        _require_admin_key(x_admin_key, active_settings.admin_key)
        return active_store.status()

    return service


def _require_bearer_token(
    authorization: str | None,
    expected_token: str,
) -> None:
    """Require the configured bearer token."""
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid USA Car bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _require_admin_key(provided_key: str | None, expected_key: str) -> None:
    """Require the configured supplier-feed administration key."""
    if provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid USA Car administration key is required.",
        )


app = create_app()
