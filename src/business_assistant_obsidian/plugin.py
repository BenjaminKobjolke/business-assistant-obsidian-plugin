"""Plugin registration — defines PydanticAI tools for Obsidian operations."""

from __future__ import annotations

import logging

from business_assistant.agent.deps import Deps
from business_assistant.plugins.registry import PluginInfo, PluginRegistry
from pydantic_ai import RunContext, Tool

from .config import load_obsidian_settings
from .constants import (
    PLUGIN_CATEGORY,
    PLUGIN_DATA_OBSIDIAN_SERVICE,
    PLUGIN_DESCRIPTION,
    PLUGIN_NAME,
    SYSTEM_PROMPT_OBSIDIAN,
)
from .obsidian_service import ObsidianService

logger = logging.getLogger(__name__)


def _get_service(ctx: RunContext[Deps]) -> ObsidianService:
    """Retrieve the ObsidianService from plugin_data."""
    return ctx.deps.plugin_data[PLUGIN_DATA_OBSIDIAN_SERVICE]


# --- List / Search tools ---


def _obsidian_list_vaults(ctx: RunContext[Deps]) -> str:
    """List all configured Obsidian vaults."""
    logger.info("obsidian_list_vaults")
    return _get_service(ctx).list_vaults()


def _obsidian_list_notes(
    ctx: RunContext[Deps], vault: str, folder: str | None = None
) -> str:
    """List notes in a vault, optionally filtered by folder."""
    logger.info("obsidian_list_notes: vault=%r folder=%r", vault, folder)
    return _get_service(ctx).list_notes(vault, folder=folder)


def _obsidian_read_note(ctx: RunContext[Deps], vault: str, note_path: str) -> str:
    """Read the full content of a note (path relative to vault root)."""
    logger.info("obsidian_read_note: vault=%r note_path=%r", vault, note_path)
    return _get_service(ctx).read_note(vault, note_path)


def _obsidian_search_notes(ctx: RunContext[Deps], vault: str, query: str) -> str:
    """Full-text search across notes in a vault (filename + content)."""
    logger.info("obsidian_search_notes: vault=%r query=%r", vault, query)
    return _get_service(ctx).search_notes(vault, query)


# --- Create / Edit tools ---


def _obsidian_create_note(
    ctx: RunContext[Deps], vault: str, note_path: str, content: str
) -> str:
    """Create a new note in a vault (note_path like 'folder/name.md')."""
    logger.info("obsidian_create_note: vault=%r note_path=%r", vault, note_path)
    return _get_service(ctx).create_note(vault, note_path, content)


def _obsidian_edit_note(
    ctx: RunContext[Deps],
    vault: str,
    note_path: str,
    content: str,
    mode: str = "append",
) -> str:
    """Edit an existing note (mode: append, prepend, or replace)."""
    logger.info(
        "obsidian_edit_note: vault=%r note_path=%r mode=%r", vault, note_path, mode
    )
    return _get_service(ctx).edit_note(vault, note_path, content, mode=mode)


# --- Folder / Tag tools ---


def _obsidian_list_folders(ctx: RunContext[Deps], vault: str) -> str:
    """List all folders in a vault."""
    logger.info("obsidian_list_folders: vault=%r", vault)
    return _get_service(ctx).list_folders(vault)


def _obsidian_list_tags(ctx: RunContext[Deps], vault: str) -> str:
    """List all tags found across notes in a vault."""
    logger.info("obsidian_list_tags: vault=%r", vault)
    return _get_service(ctx).list_tags(vault)


def register(registry: PluginRegistry) -> None:
    """Register the Obsidian plugin with the plugin registry."""
    from business_assistant.config.log_setup import add_plugin_logging

    add_plugin_logging("obsidian", "business_assistant_obsidian")

    settings = load_obsidian_settings()
    if settings is None:
        logger.info(
            "Obsidian plugin: OBSIDIAN_VAULTS not configured, skipping registration"
        )
        return

    service = ObsidianService(settings)

    tools = [
        Tool(_obsidian_list_vaults, name="obsidian_list_vaults"),
        Tool(_obsidian_list_notes, name="obsidian_list_notes"),
        Tool(_obsidian_read_note, name="obsidian_read_note"),
        Tool(_obsidian_search_notes, name="obsidian_search_notes"),
        Tool(_obsidian_create_note, name="obsidian_create_note"),
        Tool(_obsidian_edit_note, name="obsidian_edit_note"),
        Tool(_obsidian_list_folders, name="obsidian_list_folders"),
        Tool(_obsidian_list_tags, name="obsidian_list_tags"),
    ]

    info = PluginInfo(
        name=PLUGIN_NAME,
        description=PLUGIN_DESCRIPTION,
        system_prompt_extra=SYSTEM_PROMPT_OBSIDIAN,
        category=PLUGIN_CATEGORY,
    )

    registry.register(info, tools)
    registry.plugin_data[PLUGIN_DATA_OBSIDIAN_SERVICE] = service

    logger.info("Obsidian plugin registered with %d tools", len(tools))
