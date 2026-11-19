from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

_MANIFEST_RE = re.compile(
    r"<!-- CKNEXUS_SKILL_MANIFEST_BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*"
    r"<!-- CKNEXUS_SKILL_MANIFEST_END -->",
    re.DOTALL,
)


class SkillRisk(StrEnum):
    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    EXTERNAL_WRITE = "external_write"
    HIGH_IMPACT = "high_impact"


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    id: str
    version: str
    organ: str
    description: str
    capabilities: tuple[str, ...]
    risk: SkillRisk
    approval_required: bool
    executor: str
    tags: tuple[str, ...]

    @classmethod
    def from_mapping(cls, raw: dict[str, object]) -> SkillDefinition:
        skill_id = str(raw.get("id") or "").strip()
        version = str(raw.get("version") or "").strip()
        organ = str(raw.get("organ") or "").strip()
        description = str(raw.get("description") or "").strip()
        executor = str(raw.get("executor") or "").strip()
        if not all((skill_id, version, organ, description, executor)):
            raise ValueError("skill manifest contains an empty required field")
        capabilities = tuple(str(v).strip() for v in raw.get("capabilities", []) if str(v).strip())
        tags = tuple(str(v).strip().lower() for v in raw.get("tags", []) if str(v).strip())
        return cls(
            id=skill_id,
            version=version,
            organ=organ,
            description=description,
            capabilities=capabilities,
            risk=SkillRisk(str(raw.get("risk") or "read_only")),
            approval_required=bool(raw.get("approval_required", False)),
            executor=executor,
            tags=tags,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "organ": self.organ,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "risk": self.risk.value,
            "approval_required": self.approval_required,
            "executor": self.executor,
            "tags": list(self.tags),
        }


@dataclass(frozen=True, slots=True)
class AgnesSkillManifest:
    manifest_version: int
    agent: str
    skills: tuple[SkillDefinition, ...]

    @classmethod
    def load(cls, path: Path) -> AgnesSkillManifest:
        text = path.read_text(encoding="utf-8")
        match = _MANIFEST_RE.search(text)
        if match is None:
            raise ValueError("AGNES SKILL.md is missing the canonical JSON manifest block")
        raw = json.loads(match.group(1))
        if int(raw.get("manifest_version", 0)) != 1:
            raise ValueError("unsupported AGNES skill manifest version")
        skills = tuple(SkillDefinition.from_mapping(item) for item in raw.get("skills", []))
        ids = [skill.id for skill in skills]
        if not skills or len(ids) != len(set(ids)):
            raise ValueError("AGNES skill manifest must contain unique skill ids")
        return cls(manifest_version=1, agent=str(raw.get("agent") or "AGNES"), skills=skills)


class AgnesSkillRegistry:
    def __init__(self, manifest: AgnesSkillManifest) -> None:
        self.manifest = manifest
        self._by_id = {skill.id: skill for skill in manifest.skills}

    @classmethod
    def load(cls, path: Path) -> AgnesSkillRegistry:
        return cls(AgnesSkillManifest.load(path))

    def get(self, skill_id: str) -> SkillDefinition:
        try:
            return self._by_id[skill_id]
        except KeyError as exc:
            raise KeyError(f"unknown AGNES skill: {skill_id}") from exc

    def all(self) -> tuple[SkillDefinition, ...]:
        return self.manifest.skills

    def select(self, goal: str, *, limit: int = 6) -> tuple[SkillDefinition, ...]:
        tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9_-]+", goal)}
        scored: list[tuple[int, int, SkillDefinition]] = []
        for index, skill in enumerate(self.manifest.skills):
            score = len(tokens.intersection(skill.tags))
            if score:
                scored.append((-score, index, skill))
        selected = [item[2] for item in sorted(scored)[: max(1, limit)]]
        if not selected:
            selected = [
                self.get("brain.plan"),
                self.get("immune.policy_check"),
                self.get("mouth.report"),
            ]
        return tuple(selected)
