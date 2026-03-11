"""Shared test fixtures for the Obsidian plugin."""

from __future__ import annotations

import pytest

from business_assistant_obsidian.config import ObsidianSettings, VaultConfig


@pytest.fixture()
def vault_configs() -> tuple[VaultConfig, ...]:
    return (
        VaultConfig(name="TestVault", path="/tmp/test_vault"),
        VaultConfig(name="WorkVault", path="/tmp/work_vault"),
    )


@pytest.fixture()
def obsidian_settings(vault_configs: tuple[VaultConfig, ...]) -> ObsidianSettings:
    return ObsidianSettings(vaults=vault_configs)
