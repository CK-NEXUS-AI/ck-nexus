from __future__ import annotations

from pydantic import BaseModel, Field

from creator_app.core.policy_errors import PolicyViolation


class CheckpointBinding(BaseModel):
    checkpoint_id: str = Field(min_length=1)
    expected_version_hash: str = Field(min_length=1)
    observed_version_hash: str = Field(min_length=1)


class CheckpointGuard:
    """Rejects stale or substituted checkpoints before resume/fork execution."""

    @staticmethod
    def require_version_match(binding: CheckpointBinding) -> None:
        if binding.expected_version_hash != binding.observed_version_hash:
            raise PolicyViolation("checkpoint version hash mismatch")
