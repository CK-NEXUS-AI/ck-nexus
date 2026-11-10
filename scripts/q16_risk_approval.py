from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

MARKER = "CKNEXUS-Q16-RISK-APPROVED"
OWNER_LOGIN = "spinlnw10-art"
MEDIUM_MARKER = "CKNEXUS-Q16-MEDIUM-REVIEW-APPROVED"
_ATTESTATION_FIELDS = {
    "source_sha",
    "base_image",
    "image_config_digest",
    "report_sha256",
    "vulnerability_ids",
    "finding_refs",
    "expires_at",
    "rationale",
}


def _fields(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in body.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        key = key.strip().lower()
        if key not in _ATTESTATION_FIELDS:
            continue
        if key in result:
            return {}
        result[key] = value.strip()
    return result


def _owner_allowed(user: dict[str, Any], comment: dict[str, Any]) -> bool:
    return (
        user.get("login") == OWNER_LOGIN
        and user.get("type") == "User"
        and str(comment.get("author_association", "")).upper() in {"MEMBER", "OWNER"}
    )


def _independent_allowed(user: dict[str, Any], comment: dict[str, Any]) -> bool:
    login = user.get("login")
    return (
        isinstance(login, str)
        and login != OWNER_LOGIN
        and user.get("type") == "User"
        and str(comment.get("author_association", "")).upper() in {"COLLABORATOR", "MEMBER"}
    )


def _verify_attestation(
    comments: list[dict[str, Any]],
    *,
    marker: str,
    expected: dict[str, str],
    actor_allowed: Callable[[dict[str, Any], dict[str, Any]], bool],
    today: date | None,
) -> dict[str, str] | None:
    if not expected.get("vulnerability_ids") or not expected.get("finding_refs"):
        return None
    if not all(expected.values()):
        return None

    current_date = today or datetime.now(UTC).date()
    matches: list[dict[str, str]] = []
    for comment in comments:
        user = comment.get("user") or {}
        if not isinstance(user, dict) or not actor_allowed(user, comment):
            continue
        body = str(comment.get("body") or "")
        if marker not in body.splitlines():
            continue
        fields = _fields(body)
        if any(fields.get(key) != value for key, value in expected.items()):
            continue
        if not fields.get("rationale"):
            continue
        try:
            created = datetime.fromisoformat(str(comment["created_at"]).replace("Z", "+00:00"))
            expiry = date.fromisoformat(fields["expires_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if created.tzinfo is None or created.date() > current_date:
            continue
        if expiry < current_date or expiry > created.date() + timedelta(days=30):
            continue
        url = comment.get("html_url")
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            continue
        matches.append(
            {
                "actor": str(user["login"]),
                "reference": url,
                "created_at": created.astimezone(UTC).isoformat(),
                "expires_at": expiry.isoformat(),
            }
        )
    if not matches:
        return None
    return sorted(matches, key=lambda item: item["created_at"])[-1]


def _expected_fields(
    *,
    source_sha: str,
    base_image: str,
    image_config_digest: str,
    report_sha256: str,
    vulnerability_ids: set[str],
    finding_refs: set[str],
) -> dict[str, str]:
    return {
        "source_sha": source_sha,
        "base_image": base_image,
        "image_config_digest": image_config_digest,
        "report_sha256": report_sha256,
        "vulnerability_ids": ",".join(sorted(vulnerability_ids)),
        "finding_refs": ";".join(sorted(finding_refs)),
    }


def verify_owner_risk_approval(
    comments: list[dict[str, Any]],
    *,
    source_sha: str,
    base_image: str,
    image_config_digest: str,
    report_sha256: str,
    vulnerability_ids: set[str],
    finding_refs: set[str],
    today: date | None = None,
) -> dict[str, str] | None:
    """Accept only the pinned repository Owner's exact-image/finding attestation."""
    return _verify_attestation(
        comments,
        marker=MARKER,
        expected=_expected_fields(
            source_sha=source_sha,
            base_image=base_image,
            image_config_digest=image_config_digest,
            report_sha256=report_sha256,
            vulnerability_ids=vulnerability_ids,
            finding_refs=finding_refs,
        ),
        actor_allowed=_owner_allowed,
        today=today,
    )


def verify_independent_medium_review(
    comments: list[dict[str, Any]],
    *,
    source_sha: str,
    base_image: str,
    image_config_digest: str,
    report_sha256: str,
    vulnerability_ids: set[str],
    finding_refs: set[str],
    today: date | None = None,
) -> dict[str, str] | None:
    """Accept a time-limited medium-finding disposition from a non-Owner collaborator."""
    return _verify_attestation(
        comments,
        marker=MEDIUM_MARKER,
        expected=_expected_fields(
            source_sha=source_sha,
            base_image=base_image,
            image_config_digest=image_config_digest,
            report_sha256=report_sha256,
            vulnerability_ids=vulnerability_ids,
            finding_refs=finding_refs,
        ),
        actor_allowed=_independent_allowed,
        today=today,
    )
