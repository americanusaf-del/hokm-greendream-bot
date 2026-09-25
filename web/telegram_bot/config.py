"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required bot configuration is missing."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for the Telegram bot."""

    bot_token: str

    @classmethod
    def from_environment(cls) -> Settings:
        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            raise ConfigurationError(
                "BOT_TOKEN is not set. Add the bot token to the "
                "environment before starting the bot."
            )
        return cls(bot_token=token)
