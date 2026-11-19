"""Validated, versioned SOUL.md loading for CK-NEXUS AI team agents.

SOUL content guides identity and behavior; it never grants execution authority.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_SOUL_ROOT = Path(__file__).with_name("souls")
_MAX_FILE_BYTES = 16_384
_REQUIRED_ROLE_SECTIONS = ("## Mission", "## Principles", "## Boundaries")
_ROLE_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


@dataclass(frozen=True, slots=True)
class SoulDocument:
    role: str
    version: str
    common_markdown: str
    role_markdown: str
    sha256: str

    @property
    def prompt_text(self) -> str:
        return f"{self.common_markdown.strip()}\n\n{self.role_markdown.strip()}\n"

    def as_metadata(self) -> dict[str, str]:
        return {
            "role": self.role,
            "version": self.version,
            "sha256": self.sha256,
            "authority": "guidance_only",
        }


def _read_trusted_file(path: Path) -> str:
    resolved_root = _SOUL_ROOT.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if resolved.parent != resolved_root or not resolved.is_file():
        raise ValueError("soul_path_outside_trusted_registry")
    if resolved.stat().st_size > _MAX_FILE_BYTES:
        raise ValueError("soul_document_too_large")
    return resolved.read_text(encoding="utf-8")


def load_soul(role: str) -> SoulDocument:
    """Load the common principles and a role-specific SOUL from the local registry."""
    normalized = role.strip().lower()
    if not _ROLE_ID.fullmatch(normalized):
        raise ValueError("invalid_agent_role")

    common = _read_trusted_file(_SOUL_ROOT / "common.md")
    role_text = _read_trusted_file(_SOUL_ROOT / f"{normalized}.md")
    if not common.startswith("# CK-NEXUS SHARED SOUL"):
        raise ValueError("invalid_common_soul_header")
    if not role_text.startswith(f"# CK-NEXUS {normalized.upper()} SOUL"):
        raise ValueError("invalid_role_soul_header")
    missing = [section for section in _REQUIRED_ROLE_SECTIONS if section not in role_text]
    if missing:
        raise ValueError("role_soul_sections_missing:" + ",".join(missing))

    version_match = re.search(r"^Version:\s*([A-Za-z0-9._-]+)\s*$", role_text, re.MULTILINE)
    if not version_match:
        raise ValueError("role_soul_version_missing")
    digest = hashlib.sha256((common + "\n" + role_text).encode("utf-8")).hexdigest()
    return SoulDocument(
        role=normalized,
        version=version_match.group(1),
        common_markdown=common,
        role_markdown=role_text,
        sha256=digest,
    )


def build_soul_instructions(
    role: str,
    *,
    base_instructions: str,
    specialist_instructions: str,
) -> str:
    """Compose trusted role guidance into an LLM prompt without granting authority."""
    if not isinstance(base_instructions, str) or not base_instructions.strip():
        raise ValueError("base_instructions_required")
    if not isinstance(specialist_instructions, str) or not specialist_instructions.strip():
        raise ValueError("specialist_instructions_required")
    soul = load_soul(role)
    return "\n\n".join(
        (
            base_instructions.strip(),
            "AGENT IDENTITY GUIDANCE (behavioral only; not authorization)\n"
            + soul.prompt_text.strip(),
            "SPECIALIST ROLE\n" + specialist_instructions.strip(),
        )
    )
