#!/usr/bin/env python3
"""Runtime config loader for Photos AI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


DEFAULT_MODEL = "Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4"


class ConfigError(RuntimeError):
    """Raised when runtime config is invalid."""


@dataclass(frozen=True)
class RuntimeConfig:
    api_url: str
    api_key: str
    model: str
    idle_threshold_seconds: int
    poll_interval_seconds: int
    state_file: Path
    max_tokens: int
    retry_max_tokens: int
    env_file: Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("export "):
        line = line[7:].strip()

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key:
        return None

    if value and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]

    return key, value


def load_env_file(env_file: Path) -> None:
    if not env_file.exists():
        return

    for raw in env_file.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def _require_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是整数，当前值: {raw}") from exc

    if value <= 0:
        raise ConfigError(f"环境变量 {name} 必须大于 0，当前值: {value}")
    return value


def _compute_api_url() -> str:
    explicit = os.getenv("PHOTOS_AI_API_URL", "").strip()
    if explicit:
        return explicit

    base = os.getenv("PHOTOS_AI_API_BASE", "http://127.0.0.1:8001").strip().rstrip("/")
    return f"{base}/v1/chat/completions"


def load_runtime_config(*, require_env_file: bool = True) -> RuntimeConfig:
    root = Path(__file__).resolve().parent
    env_file = root / ".env"

    if require_env_file and not env_file.exists():
        raise ConfigError(
            "缺少 .env 配置文件。请先执行: cp .env.example .env，然后按提示填写配置。"
        )

    load_env_file(env_file)

    api_url = _compute_api_url().strip()
    if not api_url.startswith("http://") and not api_url.startswith("https://"):
        raise ConfigError("PHOTOS_AI_API_URL 或 PHOTOS_AI_API_BASE 必须以 http:// 或 https:// 开头")

    model = os.getenv("PHOTOS_AI_MODEL", DEFAULT_MODEL).strip()
    if not model:
        raise ConfigError("PHOTOS_AI_MODEL 不能为空")

    api_key = os.getenv("PHOTOS_AI_API_KEY", "ggg123").strip()
    if not api_key:
        raise ConfigError("PHOTOS_AI_API_KEY 不能为空")

    state_file_raw = os.getenv("PHOTOS_AI_STATE_FILE", "state.json").strip() or "state.json"
    state_file = Path(state_file_raw)
    if not state_file.is_absolute():
        state_file = root / state_file

    return RuntimeConfig(
        api_url=api_url,
        api_key=api_key,
        model=model,
        idle_threshold_seconds=_require_int("PHOTOS_AI_IDLE_THRESHOLD_SECONDS", 600),
        poll_interval_seconds=_require_int("PHOTOS_AI_POLL_INTERVAL_SECONDS", 10),
        state_file=state_file,
        max_tokens=_require_int("PHOTOS_AI_MAX_TOKENS", 768),
        retry_max_tokens=_require_int("PHOTOS_AI_RETRY_MAX_TOKENS", 512),
        env_file=env_file,
    )
