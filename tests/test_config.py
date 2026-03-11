"""Tests for configuration loading."""

from __future__ import annotations

import dataclasses

import pytest

from business_assistant_obsidian.config import (
    ObsidianSettings,
    VaultConfig,
    _parse_vault_entry,
    load_obsidian_settings,
)


class TestParseVaultEntry:
    def test_valid_entry(self) -> None:
        result = _parse_vault_entry("MyVault:/tmp/vault")
        assert result == VaultConfig(name="MyVault", path="/tmp/vault")

    def test_windows_path(self) -> None:
        result = _parse_vault_entry(r"Notes:E:\[--Sync--]\Notes_XD")
        assert result is not None
        assert result.name == "Notes"
        assert result.path == r"E:\[--Sync--]\Notes_XD"

    def test_strips_whitespace(self) -> None:
        result = _parse_vault_entry("  MyVault : /tmp/vault  ")
        assert result == VaultConfig(name="MyVault", path="/tmp/vault")

    def test_no_separator(self) -> None:
        assert _parse_vault_entry("no_separator") is None

    def test_empty_name(self) -> None:
        assert _parse_vault_entry(":/tmp/vault") is None

    def test_empty_path(self) -> None:
        assert _parse_vault_entry("MyVault:") is None

    def test_empty_string(self) -> None:
        assert _parse_vault_entry("") is None


class TestLoadObsidianSettings:
    def test_returns_none_without_env(self, monkeypatch) -> None:
        monkeypatch.delenv("OBSIDIAN_VAULTS", raising=False)
        assert load_obsidian_settings() is None

    def test_returns_none_with_empty_env(self, monkeypatch) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULTS", "")
        assert load_obsidian_settings() is None

    def test_single_vault(self, monkeypatch) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULTS", "MyVault:/tmp/vault")
        settings = load_obsidian_settings()
        assert settings is not None
        assert len(settings.vaults) == 1
        assert settings.vaults[0].name == "MyVault"
        assert settings.vaults[0].path == "/tmp/vault"

    def test_multiple_vaults(self, monkeypatch) -> None:
        monkeypatch.setenv(
            "OBSIDIAN_VAULTS",
            "Vault1:/tmp/v1,Vault2:/tmp/v2",
        )
        settings = load_obsidian_settings()
        assert settings is not None
        assert len(settings.vaults) == 2
        assert settings.vaults[0].name == "Vault1"
        assert settings.vaults[1].name == "Vault2"

    def test_windows_paths(self, monkeypatch) -> None:
        monkeypatch.setenv(
            "OBSIDIAN_VAULTS",
            r"Employees:E:\[--Sync--]\Notes_XD_Employees,"
            r"Intern:E:\[--Sync--]\Notes_XD_Intern",
        )
        settings = load_obsidian_settings()
        assert settings is not None
        assert len(settings.vaults) == 2
        assert settings.vaults[0].name == "Employees"
        assert settings.vaults[0].path == r"E:\[--Sync--]\Notes_XD_Employees"
        assert settings.vaults[1].name == "Intern"
        assert settings.vaults[1].path == r"E:\[--Sync--]\Notes_XD_Intern"

    def test_skips_malformed_entries(self, monkeypatch) -> None:
        monkeypatch.setenv(
            "OBSIDIAN_VAULTS",
            "Good:/tmp/good,bad_entry,:/tmp/noname,nopath:,Also_Good:/tmp/ok",
        )
        settings = load_obsidian_settings()
        assert settings is not None
        assert len(settings.vaults) == 2
        assert settings.vaults[0].name == "Good"
        assert settings.vaults[1].name == "Also_Good"

    def test_returns_none_if_all_malformed(self, monkeypatch) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULTS", "bad,also_bad")
        assert load_obsidian_settings() is None


class TestFrozenDataclasses:
    def test_vault_config_is_frozen(self) -> None:
        config = VaultConfig(name="test", path="/tmp")
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.name = "changed"  # type: ignore[misc]

    def test_obsidian_settings_is_frozen(self) -> None:
        settings = ObsidianSettings(vaults=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.vaults = ()  # type: ignore[misc]
