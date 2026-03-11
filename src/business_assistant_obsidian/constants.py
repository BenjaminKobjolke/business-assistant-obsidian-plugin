"""Plugin-specific string constants."""

# Environment variable names
ENV_OBSIDIAN_VAULTS = "OBSIDIAN_VAULTS"

# Plugin name and category
PLUGIN_NAME = "obsidian"
PLUGIN_CATEGORY = "notes"
PLUGIN_DESCRIPTION = "Obsidian vault note management"

# Plugin data keys
PLUGIN_DATA_OBSIDIAN_SERVICE = "obsidian_service"

# Vault configuration parsing
VAULT_SEPARATOR = ","
VAULT_NAME_PATH_SEPARATOR = ":"

# File system
MD_EXTENSION = ".md"
HIDDEN_DIRS = {".obsidian", ".trash"}

# Tag extraction
TAG_PATTERN = r"(?:^|\s)#([a-zA-Z0-9_/-]+)"

# Edit modes
EDIT_MODE_APPEND = "append"
EDIT_MODE_PREPEND = "prepend"
EDIT_MODE_REPLACE = "replace"
VALID_EDIT_MODES = {EDIT_MODE_APPEND, EDIT_MODE_PREPEND, EDIT_MODE_REPLACE}

# Search
DEFAULT_SEARCH_LIMIT = 50

# Error messages
ERR_VAULT_NOT_FOUND = "Vault '{vault}' not found. Available vaults: {available}"
ERR_NOTE_NOT_FOUND = "Note '{note}' not found in vault '{vault}'."
ERR_NOTE_ALREADY_EXISTS = "Note '{note}' already exists in vault '{vault}'."
ERR_INVALID_EDIT_MODE = "Invalid edit mode '{mode}'. Use 'append', 'prepend', or 'replace'."
ERR_PATH_TRAVERSAL = "Invalid note path '{note}': path must stay within the vault."
ERR_MOVE_SAME_PATH = "Source and destination are the same: '{note}'."

# System prompt extra
SYSTEM_PROMPT_OBSIDIAN = """You have access to Obsidian vault tools for managing notes:

## Tools
- obsidian_list_vaults: List all configured vaults with their names
- obsidian_list_notes(vault, folder=None): List notes in a vault, optionally filtered by folder
- obsidian_read_note(vault, note_path): Read note content (path relative to vault root)
- obsidian_search_notes(vault, query): Full-text search across notes (filename + content)
- obsidian_create_note(vault, note_path, content): Create a new note ("folder/name.md")
- obsidian_edit_note(vault, note_path, content, mode="append"): Edit a note (append/prepend/replace)
- obsidian_move_note(vault, from_path, to_path): Move/rename a note
- obsidian_delete_note(vault, note_path): Delete a note
- obsidian_list_folders(vault): List all folders in a vault
- obsidian_list_tags(vault): List all tags found across notes in a vault

## Usage
- The vault parameter is always the vault NAME (e.g., "Notes_XD_Employees"), not a file path.
- note_path is relative to the vault root (e.g., "Projects/meeting-notes.md").
- Notes are Markdown (.md) files. Always include the .md extension in note_path.
- Tags use #tag syntax in Obsidian notes.

## Creating / Editing / Moving / Deleting notes — IMPORTANT
When the user asks to create, edit, move, or delete a note:
1. Show a preview of what will be changed
2. Ask for confirmation before proceeding
3. ONLY call the tool after explicit user confirmation

## Formatting — CRITICAL
- Tool results return JSON. Present information in natural language.
- NEVER expose file system paths to the user. Use vault names and relative note paths only."""
