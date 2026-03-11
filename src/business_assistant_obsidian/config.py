"""Obsidian vault settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .constants import ENV_OBSIDIAN_VAULTS, VAULT_NAME_PATH_SEPARATOR, VAULT_SEPARATOR


@dataclass(frozen=True)
class VaultConfig:
    """Configuration for a single Obsidian vault."""

    name: str
    path: str


@dataclass(frozen=True)
class ObsidianSettings:
    """Obsidian plugin settings."""

    vaults: tuple[VaultConfig, ...]


def _parse_vault_entry(entry: str) -> VaultConfig | None:
    """Parse a single 'name:path' vault entry.

    Returns None if the entry is malformed.
    Uses partition to split on the first colon only, since Windows paths
    contain colons (e.g. E:\\path).
    """
    entry = entry.strip()
    if VAULT_NAME_PATH_SEPARATOR not in entry:
        return None
    name, _, path = entry.partition(VAULT_NAME_PATH_SEPARATOR)
    name = name.strip()
    path = path.strip()
    if not name or not path:
        return None
    return VaultConfig(name=name, path=path)


def load_obsidian_settings() -> ObsidianSettings | None:
    """Load Obsidian settings from environment variables.

    Returns None if OBSIDIAN_VAULTS is not configured.
    """
    raw = os.environ.get(ENV_OBSIDIAN_VAULTS, "")
    if not raw:
        return None

    vaults: list[VaultConfig] = []
    for entry in raw.split(VAULT_SEPARATOR):
        config = _parse_vault_entry(entry)
        if config is not None:
            vaults.append(config)

    if not vaults:
        return None

    return ObsidianSettings(vaults=tuple(vaults))
