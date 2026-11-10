from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

MARKER = "CKNEXUS-Q16-RISK-APPROVED"
OWNER_LOGIN = "spinlnw10-art"


def _fields(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in body.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            key = key.strip().lower()
            if key in {
                "source_sha",
                "image_config_digest",
                "report_sha256",
                "vulnerability_ids",
                "finding_refs",
                "expires_at",
                "rationale",
            }:
                if key in result:
                    return {}
                result[key] = value.strip()
    return result


def verify_owner_risk_approval(
    comments: list[dict[str, Any]],
    *,
    source_sha: str,
    image_config_digest: str,
    report_sha256: str,
    vulnerability_ids: set[str],
    finding_refs: set[str],
    today: date | None = None,
) -> dict[str, str] | None:
    """Accept only a pinned repository Owner's authenticated, exact-image attestation."""
    if not vulnerability_ids:
        return None
    current_date = today or datetime.now(UTC).date()
    expected = {
        "source_sha": source_sha,
        "image_config_digest": image_config_digest,
        "report_sha256": report_sha256,
        "vulnerability_ids": ",".join(sorted(vulnerability_ids)),
        "finding_refs": ";".join(sorted(finding_refs)),
    }
    matches: list[dict[str, str]] = []
    for comment in comments:
        user = comment.get("user") or {}
        if (
            user.get("login") != OWNER_LOGIN
            or user.get("type") != "User"
            or str(comment.get("author_association", "")).upper() not in {"MEMBER", "OWNER"}
        ):
            continue
        body = str(comment.get("body") or "")
        if MARKER not in body.splitlines():
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
                "actor": OWNER_LOGIN,
                "reference": url,
                "created_at": created.astimezone(UTC).isoformat(),
                "expires_at": expiry.isoformat(),
            }
        )
    if not matches:
        return None
    return sorted(matches, key=lambda item: item["created_at"])[-1]


def verify_independent_medium_review(
    comments: list[dict[str, Any]],
    *,
    source_sha: str,
    image_config_digest: str,
    report_sha256: str,
    vulnerability_ids: set[str],
    finding_refs: set[str],
    today: date | None = None,
) -> dict[str, str] | None:
    """Accept a time-limited medium-finding disposition from a non-Owner collaborator."""
    if not vulnerability_ids:
        return None
    current_date = today or datetime.now(UTC).date()
    expected = {
        "source_sha": source_sha,
        "image_config_digest": image_config_digest,
        "report_sha256": report_sha256,
        "vulnerability_ids": ",".join(sorted(vulnerability_ids)),
        "finding_refs": ";".join(sorted(finding_refs)),
    }
    matches: list[dict[str, str]] = []
    for comment in comments:
        user = comment.get("user") or {}
        login = user.get("login")
        if (
            not isinstance(login, str)
            or login == OWNER_LOGIN
            or user.get("type") != "User"
            or str(comment.get("author_association", "")).upper() not in {"COLLABORATOR", "MEMBER"}
        ):
            continue
        body = str(comment.get("body") or "")
        if "CKNEXUS-Q16-MEDIUM-REVIEW-APPROVED" not in body.splitlines():
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
                "actor": login,
                "reference": url,
                "created_at": created.astimezone(UTC).isoformat(),
                "expires_at": expiry.isoformat(),
            }
        )
    if not matches:
        return None
    return sorted(matches, key=lambda item: item["created_at"])[-1]
