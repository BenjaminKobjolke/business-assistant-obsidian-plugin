"""ObsidianService — high-level vault operations returning formatted strings."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Generator
from pathlib import Path

from .config import ObsidianSettings, VaultConfig
from .constants import (
    DEFAULT_SEARCH_LIMIT,
    EDIT_MODE_APPEND,
    EDIT_MODE_REPLACE,
    ERR_INVALID_EDIT_MODE,
    ERR_NOTE_ALREADY_EXISTS,
    ERR_NOTE_NOT_FOUND,
    ERR_PATH_TRAVERSAL,
    ERR_VAULT_NOT_FOUND,
    HIDDEN_DIRS,
    MD_EXTENSION,
    TAG_PATTERN,
    VALID_EDIT_MODES,
)

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(TAG_PATTERN, re.MULTILINE)


class ObsidianService:
    """High-level Obsidian vault operations returning formatted strings for LLM consumption."""

    def __init__(self, settings: ObsidianSettings) -> None:
        self._settings = settings
        self._vault_map: dict[str, VaultConfig] = {v.name: v for v in settings.vaults}

    def _resolve_vault(self, vault_name: str) -> VaultConfig:
        """Validate and return the VaultConfig for a given name."""
        config = self._vault_map.get(vault_name)
        if config is None:
            available = ", ".join(sorted(self._vault_map.keys()))
            raise ValueError(ERR_VAULT_NOT_FOUND.format(vault=vault_name, available=available))
        return config

    def _resolve_note_path(self, vault_config: VaultConfig, note_path: str) -> Path:
        """Join vault root with relative note path, preventing path traversal."""
        vault_root = Path(vault_config.path).resolve()
        full_path = (vault_root / note_path).resolve()
        if not full_path.is_relative_to(vault_root):
            raise ValueError(ERR_PATH_TRAVERSAL.format(note=note_path))
        return full_path

    @staticmethod
    def _is_hidden(path: Path, vault_root: Path) -> bool:
        """Check if any path component relative to vault root is a hidden directory."""
        try:
            rel = path.relative_to(vault_root)
        except ValueError:
            return True
        return any(part in HIDDEN_DIRS or part.startswith(".") for part in rel.parts)

    def _iter_notes(self, vault_root: Path) -> Generator[Path, None, None]:
        """Walk all .md files in the vault, skipping hidden directories."""
        for md_file in vault_root.rglob(f"*{MD_EXTENSION}"):
            if not self._is_hidden(md_file, vault_root):
                yield md_file

    # --- Public API (all return str) ---

    def list_vaults(self) -> str:
        """List all configured vaults."""
        vaults = [{"name": v.name} for v in self._settings.vaults]
        return json.dumps({"vaults": vaults})

    def list_notes(self, vault_name: str, folder: str | None = None) -> str:
        """List notes in a vault, optionally filtered by folder."""
        try:
            config = self._resolve_vault(vault_name)
            vault_root = Path(config.path).resolve()

            if folder:
                search_root = (vault_root / folder).resolve()
                if not search_root.is_relative_to(vault_root):
                    raise ValueError(ERR_PATH_TRAVERSAL.format(note=folder))
                if not search_root.is_dir():
                    return json.dumps({"vault": vault_name, "notes": []})
                notes_iter = search_root.rglob(f"*{MD_EXTENSION}")
            else:
                notes_iter = self._iter_notes(vault_root)

            notes = []
            for md_file in notes_iter:
                if folder and self._is_hidden(md_file, vault_root):
                    continue
                rel_path = md_file.relative_to(vault_root)
                notes.append({
                    "path": str(rel_path).replace("\\", "/"),
                    "name": md_file.stem,
                })

            notes.sort(key=lambda n: n["path"])
            return json.dumps({"vault": vault_name, "notes": notes})
        except Exception as e:
            return f"Error listing notes: {e}"

    def read_note(self, vault_name: str, note_path: str) -> str:
        """Read the full content of a note."""
        try:
            config = self._resolve_vault(vault_name)
            full_path = self._resolve_note_path(config, note_path)

            if not full_path.is_file():
                return ERR_NOTE_NOT_FOUND.format(note=note_path, vault=vault_name)

            content = full_path.read_text(encoding="utf-8")
            return json.dumps({
                "vault": vault_name,
                "path": note_path,
                "content": content,
            })
        except Exception as e:
            return f"Error reading note: {e}"

    def search_notes(self, vault_name: str, query: str) -> str:
        """Full-text search across notes in a vault (filename + content)."""
        try:
            config = self._resolve_vault(vault_name)
            vault_root = Path(config.path).resolve()
            query_lower = query.lower()

            results: list[dict] = []
            for md_file in self._iter_notes(vault_root):
                rel_path = str(md_file.relative_to(vault_root)).replace("\\", "/")

                # Check filename match
                if query_lower in md_file.name.lower():
                    results.append({"path": rel_path, "snippet": f"Filename match: {md_file.name}"})
                    if len(results) >= DEFAULT_SEARCH_LIMIT:
                        break
                    continue

                # Check content match
                try:
                    content = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue

                for line in content.splitlines():
                    if query_lower in line.lower():
                        snippet = line.strip()[:200]
                        results.append({"path": rel_path, "snippet": snippet})
                        break

                if len(results) >= DEFAULT_SEARCH_LIMIT:
                    break

            return json.dumps({
                "vault": vault_name,
                "query": query,
                "results": results,
            })
        except Exception as e:
            return f"Error searching notes: {e}"

    def create_note(self, vault_name: str, note_path: str, content: str) -> str:
        """Create a new note in a vault."""
        try:
            config = self._resolve_vault(vault_name)
            full_path = self._resolve_note_path(config, note_path)

            if full_path.exists():
                return ERR_NOTE_ALREADY_EXISTS.format(note=note_path, vault=vault_name)

            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return f"Note created: {note_path}"
        except Exception as e:
            return f"Error creating note: {e}"

    def edit_note(
        self, vault_name: str, note_path: str, content: str, mode: str = EDIT_MODE_APPEND
    ) -> str:
        """Edit an existing note (append, prepend, or replace)."""
        try:
            if mode not in VALID_EDIT_MODES:
                return ERR_INVALID_EDIT_MODE.format(mode=mode)

            config = self._resolve_vault(vault_name)
            full_path = self._resolve_note_path(config, note_path)

            if not full_path.is_file():
                return ERR_NOTE_NOT_FOUND.format(note=note_path, vault=vault_name)

            if mode == EDIT_MODE_REPLACE:
                full_path.write_text(content, encoding="utf-8")
            else:
                existing = full_path.read_text(encoding="utf-8")
                if mode == EDIT_MODE_APPEND:
                    new_content = existing + "\n" + content
                else:  # prepend
                    new_content = content + "\n" + existing
                full_path.write_text(new_content, encoding="utf-8")

            return f"Note updated ({mode}): {note_path}"
        except Exception as e:
            return f"Error editing note: {e}"

    def list_folders(self, vault_name: str) -> str:
        """List all folders in a vault."""
        try:
            config = self._resolve_vault(vault_name)
            vault_root = Path(config.path).resolve()

            folders: list[str] = []
            for entry in vault_root.rglob("*"):
                if entry.is_dir() and not self._is_hidden(entry, vault_root):
                    rel = str(entry.relative_to(vault_root)).replace("\\", "/")
                    folders.append(rel)

            folders.sort()
            return json.dumps({"vault": vault_name, "folders": folders})
        except Exception as e:
            return f"Error listing folders: {e}"

    def list_tags(self, vault_name: str) -> str:
        """List all tags found across notes in a vault."""
        try:
            config = self._resolve_vault(vault_name)
            vault_root = Path(config.path).resolve()

            tags: set[str] = set()
            for md_file in self._iter_notes(vault_root):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                tags.update(_TAG_RE.findall(content))

            return json.dumps({"vault": vault_name, "tags": sorted(tags)})
        except Exception as e:
            return f"Error listing tags: {e}"
