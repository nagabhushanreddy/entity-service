"""Configuration settings for Entity API with flexible config loading."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from utils import load_settings


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./entity.db"
    DB_ECHO: bool = False

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Entity API"

    # Service
    SERVICE_NAME: str = "entity-api"
    LOG_LEVEL: str = "INFO"


class Config:
    """Config object that merges file-based settings with env-driven defaults."""

    def __init__(self, settings: Settings, config_dir: str | Path = "config") -> None:
        self.settings = settings
        self.config_dir = Path(config_dir)
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._create_directories()

    def _load_config(self) -> None:
        """Load and merge all JSON config files from the config directory."""
        if not self.config_dir.exists():
            self._config = {}
            return

        files: List[Path] = sorted(self.config_dir.glob("*.json"))
        merged: Dict[str, Any] = {}

        for file_path in files:
            try:
                file_data = json.loads(file_path.read_text())
            except json.JSONDecodeError:
                continue
            self._merge_dicts(merged, file_data)

        self._config = self._resolve_env_vars(merged)

    def _merge_dicts(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively merge one config mapping into another."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_dicts(base[key], value)
            else:
                base[key] = value

    def _resolve_env_vars(self, value: Any) -> Any:
        """Replace ${VAR_NAME} patterns with environment variable values."""
        if isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]
        if isinstance(value, str):
            pattern = r"\$\{([^}]+)\}"
            result = value
            for var_name in re.findall(pattern, value):
                env_val = os.getenv(var_name, "")
                result = result.replace(f"${{{var_name}}}", env_val)
            return result
        return value

    def _create_directories(self) -> None:
        """Create directories declared under a `paths` section if present."""
        paths_cfg = self.get("paths", {})
        if not isinstance(paths_cfg, dict):
            return

        for key, path_value in paths_cfg.items():
            if isinstance(path_value, dict):
                for nested_value in path_value.values():
                    if nested_value:
                        Path(nested_value).mkdir(parents=True, exist_ok=True)
            elif path_value:
                Path(path_value).mkdir(parents=True, exist_ok=True)

    def get(self, key_path: str, default: Any | None = None) -> Any:
        """Retrieve config value via dot notation with default fallback."""
        keys = key_path.split(".")
        value: Any = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_path(self, key_path: str, default: str | None = None) -> Path:
        """Return a config path as a Path object."""
        path_str = self.get(key_path, default)
        return Path(path_str).expanduser() if path_str else Path()

    def list_config_files(self) -> List[str]:
        """List JSON config files detected in the config directory."""
        if not self.config_dir.exists():
            return []
        return [path.name for path in sorted(self.config_dir.glob("*.json"))]

    def reload(self) -> None:
        """Reload file-based configuration from disk."""
        self._load_config()
        self._create_directories()

    def get_all(self) -> Dict[str, Any]:
        """Return a shallow copy of file-derived configuration."""
        return dict(self._config)

    @property
    def database_url(self) -> str:
        return self.get("database.url", self.settings.DATABASE_URL)

    @property
    def db_echo(self) -> bool:
        return bool(self.get("database.echo", self.settings.DB_ECHO))

    @property
    def api_prefix(self) -> str:
        return self.get("api.prefix", self.settings.API_V1_STR)

    @property
    def project_name(self) -> str:
        return self.get("api.project_name", self.settings.PROJECT_NAME)

    @property
    def service_name(self) -> str:
        return self.get("service.name", self.settings.SERVICE_NAME)

    @property
    def log_level(self) -> str:
        return self.get("logging.level", self.settings.LOG_LEVEL)

    @property
    def log_file(self) -> Path:
        return self.get_path("logging.file")


settings = load_settings(Settings, env_file=".env")
config = Config(settings=settings, config_dir="config")
