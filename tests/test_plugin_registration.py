"""Tests for plugin registration."""

from __future__ import annotations

from unittest.mock import patch

from business_assistant.plugins.registry import PluginRegistry

from business_assistant_obsidian.constants import PLUGIN_DATA_OBSIDIAN_SERVICE
from business_assistant_obsidian.plugin import register


class TestPluginRegistration:
    def test_register_skips_without_config(self, monkeypatch) -> None:
        monkeypatch.delenv("OBSIDIAN_VAULTS", raising=False)
        registry = PluginRegistry()
        register(registry)
        assert registry.all_tools() == []

    @patch("business_assistant_obsidian.plugin.ObsidianService")
    def test_register_with_config(self, mock_service_cls, monkeypatch) -> None:
        monkeypatch.setenv(
            "OBSIDIAN_VAULTS",
            "TestVault:/tmp/test_vault,WorkVault:/tmp/work_vault",
        )

        registry = PluginRegistry()
        register(registry)

        assert len(registry.all_tools()) == 10
        assert len(registry.plugins) == 1
        assert registry.plugins[0].name == "obsidian"
        assert registry.system_prompt_extras() != ""

    @patch("business_assistant_obsidian.plugin.ObsidianService")
    def test_register_stores_service_in_plugin_data(
        self, mock_service_cls, monkeypatch
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULTS", "TestVault:/tmp/test_vault")

        registry = PluginRegistry()
        register(registry)

        assert PLUGIN_DATA_OBSIDIAN_SERVICE in registry.plugin_data
        assert (
            registry.plugin_data[PLUGIN_DATA_OBSIDIAN_SERVICE]
            is mock_service_cls.return_value
        )
