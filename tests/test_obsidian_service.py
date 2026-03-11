"""Tests for ObsidianService."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from business_assistant_obsidian.config import ObsidianSettings, VaultConfig
from business_assistant_obsidian.obsidian_service import ObsidianService


@pytest.fixture()
def vault_root(tmp_path: Path) -> Path:
    """Create a temporary vault structure for testing."""
    # Create directories
    (tmp_path / "Projects").mkdir()
    (tmp_path / "Daily").mkdir()
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".trash").mkdir()

    # Create notes
    (tmp_path / "readme.md").write_text("# Welcome\nMain vault readme", encoding="utf-8")
    (tmp_path / "Projects" / "project-a.md").write_text(
        "# Project A\nDetails about #project-a\n#important", encoding="utf-8"
    )
    (tmp_path / "Projects" / "project-b.md").write_text(
        "# Project B\nDetails about #project-b", encoding="utf-8"
    )
    (tmp_path / "Daily" / "2026-03-11.md").write_text(
        "# Daily Note\nToday's notes #daily", encoding="utf-8"
    )
    # Hidden dir files should be skipped
    (tmp_path / ".obsidian" / "config.md").write_text("config", encoding="utf-8")
    (tmp_path / ".trash" / "deleted.md").write_text("deleted", encoding="utf-8")

    return tmp_path


@pytest.fixture()
def service(vault_root: Path) -> ObsidianService:
    settings = ObsidianSettings(
        vaults=(
            VaultConfig(name="TestVault", path=str(vault_root)),
            VaultConfig(name="EmptyVault", path=str(vault_root / "nonexistent")),
        )
    )
    return ObsidianService(settings)


class TestListVaults:
    def test_returns_vault_names(self, service: ObsidianService) -> None:
        result = json.loads(service.list_vaults())
        assert result == {"vaults": [{"name": "TestVault"}, {"name": "EmptyVault"}]}


class TestListNotes:
    def test_lists_all_notes(self, service: ObsidianService) -> None:
        result = json.loads(service.list_notes("TestVault"))
        paths = [n["path"] for n in result["notes"]]
        assert "readme.md" in paths
        assert "Projects/project-a.md" in paths
        assert "Projects/project-b.md" in paths
        assert "Daily/2026-03-11.md" in paths

    def test_excludes_hidden_dirs(self, service: ObsidianService) -> None:
        result = json.loads(service.list_notes("TestVault"))
        paths = [n["path"] for n in result["notes"]]
        for p in paths:
            assert not p.startswith(".obsidian")
            assert not p.startswith(".trash")

    def test_filter_by_folder(self, service: ObsidianService) -> None:
        result = json.loads(service.list_notes("TestVault", folder="Projects"))
        paths = [n["path"] for n in result["notes"]]
        assert len(paths) == 2
        assert "Projects/project-a.md" in paths
        assert "Projects/project-b.md" in paths

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.list_notes("NonExistent")
        assert "not found" in result

    def test_nonexistent_folder_returns_empty(self, service: ObsidianService) -> None:
        result = json.loads(service.list_notes("TestVault", folder="NoSuchFolder"))
        assert result["notes"] == []


class TestReadNote:
    def test_reads_content(self, service: ObsidianService) -> None:
        result = json.loads(service.read_note("TestVault", "readme.md"))
        assert result["vault"] == "TestVault"
        assert result["path"] == "readme.md"
        assert "# Welcome" in result["content"]

    def test_reads_nested_note(self, service: ObsidianService) -> None:
        result = json.loads(service.read_note("TestVault", "Projects/project-a.md"))
        assert "# Project A" in result["content"]

    def test_note_not_found(self, service: ObsidianService) -> None:
        result = service.read_note("TestVault", "nonexistent.md")
        assert "not found" in result

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.read_note("NonExistent", "readme.md")
        assert "not found" in result

    def test_path_traversal_blocked(self, service: ObsidianService) -> None:
        result = service.read_note("TestVault", "../../etc/passwd")
        assert "must stay within" in result or "Error" in result


class TestSearchNotes:
    def test_search_by_filename(self, service: ObsidianService) -> None:
        result = json.loads(service.search_notes("TestVault", "project-a"))
        assert len(result["results"]) >= 1
        assert any("project-a" in r["path"] for r in result["results"])

    def test_search_by_content(self, service: ObsidianService) -> None:
        result = json.loads(service.search_notes("TestVault", "Today's notes"))
        assert len(result["results"]) >= 1

    def test_case_insensitive(self, service: ObsidianService) -> None:
        result = json.loads(service.search_notes("TestVault", "PROJECT A"))
        assert len(result["results"]) >= 1

    def test_no_results(self, service: ObsidianService) -> None:
        result = json.loads(service.search_notes("TestVault", "zzz_no_match_zzz"))
        assert result["results"] == []

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.search_notes("NonExistent", "query")
        assert "not found" in result


class TestCreateNote:
    def test_creates_note(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.create_note("TestVault", "new-note.md", "# New Note")
        assert "created" in result.lower()
        assert (vault_root / "new-note.md").is_file()
        assert (vault_root / "new-note.md").read_text(encoding="utf-8") == "# New Note"

    def test_creates_with_folder(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.create_note("TestVault", "NewFolder/note.md", "content")
        assert "created" in result.lower()
        assert (vault_root / "NewFolder" / "note.md").is_file()

    def test_already_exists(self, service: ObsidianService) -> None:
        result = service.create_note("TestVault", "readme.md", "overwrite")
        assert "already exists" in result

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.create_note("NonExistent", "note.md", "content")
        assert "not found" in result

    def test_path_traversal_blocked(self, service: ObsidianService) -> None:
        result = service.create_note("TestVault", "../../evil.md", "bad")
        assert "must stay within" in result or "Error" in result


class TestEditNote:
    def test_append(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.edit_note("TestVault", "readme.md", "Appended text", mode="append")
        assert "updated" in result.lower()
        content = (vault_root / "readme.md").read_text(encoding="utf-8")
        assert content.endswith("Appended text")
        assert "# Welcome" in content

    def test_prepend(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.edit_note("TestVault", "readme.md", "Prepended text", mode="prepend")
        assert "updated" in result.lower()
        content = (vault_root / "readme.md").read_text(encoding="utf-8")
        assert content.startswith("Prepended text")
        assert "# Welcome" in content

    def test_replace(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.edit_note("TestVault", "readme.md", "Replaced", mode="replace")
        assert "updated" in result.lower()
        content = (vault_root / "readme.md").read_text(encoding="utf-8")
        assert content == "Replaced"

    def test_invalid_mode(self, service: ObsidianService) -> None:
        result = service.edit_note("TestVault", "readme.md", "text", mode="invalid")
        assert "Invalid edit mode" in result

    def test_note_not_found(self, service: ObsidianService) -> None:
        result = service.edit_note("TestVault", "nonexistent.md", "text")
        assert "not found" in result

    def test_default_mode_is_append(self, service: ObsidianService, vault_root: Path) -> None:
        service.edit_note("TestVault", "readme.md", "Default append")
        content = (vault_root / "readme.md").read_text(encoding="utf-8")
        assert content.endswith("Default append")


class TestMoveNote:
    def test_moves_note(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.move_note("TestVault", "readme.md", "Daily/readme.md")
        assert "moved" in result.lower()
        assert not (vault_root / "readme.md").exists()
        assert (vault_root / "Daily" / "readme.md").is_file()

    def test_moves_to_new_folder(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.move_note("TestVault", "readme.md", "Archive/readme.md")
        assert "moved" in result.lower()
        assert (vault_root / "Archive" / "readme.md").is_file()

    def test_rename_note(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.move_note("TestVault", "readme.md", "index.md")
        assert "moved" in result.lower()
        assert not (vault_root / "readme.md").exists()
        assert (vault_root / "index.md").is_file()

    def test_source_not_found(self, service: ObsidianService) -> None:
        result = service.move_note("TestVault", "nonexistent.md", "target.md")
        assert "not found" in result

    def test_destination_already_exists(self, service: ObsidianService) -> None:
        result = service.move_note(
            "TestVault", "readme.md", "Projects/project-a.md"
        )
        assert "already exists" in result

    def test_same_path(self, service: ObsidianService) -> None:
        result = service.move_note("TestVault", "readme.md", "readme.md")
        assert "same" in result.lower()

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.move_note("NonExistent", "a.md", "b.md")
        assert "not found" in result

    def test_path_traversal_blocked(self, service: ObsidianService) -> None:
        result = service.move_note("TestVault", "readme.md", "../../evil.md")
        assert "must stay within" in result or "Error" in result

    def test_preserves_content(self, service: ObsidianService, vault_root: Path) -> None:
        original = (vault_root / "readme.md").read_text(encoding="utf-8")
        service.move_note("TestVault", "readme.md", "moved.md")
        moved = (vault_root / "moved.md").read_text(encoding="utf-8")
        assert moved == original


class TestDeleteNote:
    def test_deletes_note(self, service: ObsidianService, vault_root: Path) -> None:
        result = service.delete_note("TestVault", "readme.md")
        assert "deleted" in result.lower()
        assert not (vault_root / "readme.md").exists()

    def test_note_not_found(self, service: ObsidianService) -> None:
        result = service.delete_note("TestVault", "nonexistent.md")
        assert "not found" in result

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.delete_note("NonExistent", "readme.md")
        assert "not found" in result

    def test_path_traversal_blocked(self, service: ObsidianService) -> None:
        result = service.delete_note("TestVault", "../../etc/passwd")
        assert "must stay within" in result or "Error" in result


class TestListFolders:
    def test_lists_folders(self, service: ObsidianService) -> None:
        result = json.loads(service.list_folders("TestVault"))
        assert "Projects" in result["folders"]
        assert "Daily" in result["folders"]

    def test_excludes_hidden_dirs(self, service: ObsidianService) -> None:
        result = json.loads(service.list_folders("TestVault"))
        for folder in result["folders"]:
            assert not folder.startswith(".")

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.list_folders("NonExistent")
        assert "not found" in result


class TestListTags:
    def test_extracts_tags(self, service: ObsidianService) -> None:
        result = json.loads(service.list_tags("TestVault"))
        tags = result["tags"]
        assert "project-a" in tags
        assert "project-b" in tags
        assert "daily" in tags
        assert "important" in tags

    def test_tags_are_sorted(self, service: ObsidianService) -> None:
        result = json.loads(service.list_tags("TestVault"))
        tags = result["tags"]
        assert tags == sorted(tags)

    def test_vault_not_found(self, service: ObsidianService) -> None:
        result = service.list_tags("NonExistent")
        assert "not found" in result
