"""Runtime configuration for the USA Car service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Store environment-driven service settings."""

    inventory_path: Path
    api_login: str
    api_password: str
    access_token: str
    admin_key: str

    @classmethod
    def from_environment(cls) -> Settings:
        """Build settings from environment variables."""
        return cls(
            inventory_path=Path(
                os.environ.get(
                    "USA_CAR_INVENTORY_PATH",
                    "/data/current_inventory.csv",
                )
            ),
            api_login=os.environ.get("USA_CAR_API_LOGIN", "demo-dealer"),
            api_password=os.environ.get(
                "USA_CAR_API_PASSWORD",
                "demo-password",
            ),
            access_token=os.environ.get(
                "USA_CAR_ACCESS_TOKEN",
                "demo-access-token",
            ),
            admin_key=os.environ.get(
                "USA_CAR_ADMIN_KEY",
                "demo-admin-key",
            ),
        )
