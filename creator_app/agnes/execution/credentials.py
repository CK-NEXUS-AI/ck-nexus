from __future__ import annotations

from dataclasses import dataclass

from creator_app.credential_broker import CredentialBroker, CredentialId, SecretLease

from .request import SkillExecutionRequest


class CredentialLeaseDenied(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class CredentialLeaseBundle:
    leases: tuple[SecretLease, ...]

    def metadata(self) -> list[dict[str, str]]:
        return [
            {
                "credential_id": lease.credential_id.value,
                "consumer": lease.consumer,
                "source": lease.source,
            }
            for lease in self.leases
        ]


class CredentialLeaseService:
    def __init__(self, broker: CredentialBroker | None) -> None:
        self._broker = broker

    def acquire(self, request: SkillExecutionRequest) -> CredentialLeaseBundle:
        if not request.credential_requirements:
            return CredentialLeaseBundle(())
        if self._broker is None:
            raise CredentialLeaseDenied("credential_broker_unavailable")
        leases: list[SecretLease] = []
        for requirement in request.credential_requirements:
            try:
                credential_id = CredentialId(requirement.credential_id)
            except ValueError as exc:
                raise CredentialLeaseDenied("unknown_credential_id") from exc
            lease = self._broker.acquire(credential_id, consumer=requirement.consumer)
            # Explicitly forbid credentials whose source claims to be a direct user secret.
            if lease.source.lower().startswith("user"):
                raise CredentialLeaseDenied("forbidden_user_secret_source")
            leases.append(lease)
        return CredentialLeaseBundle(tuple(leases))
