# CK-NEXUS Trusted Verifier Image V1

This image is a Post-P0 development verifier used only after a patch has passed the independent static verifier.

Trust properties:

- the base image is resolved to an exact registry digest before build;
- project dependencies come from the repository `uv.lock` using frozen sync;
- the verifier has a fixed `/cknexus/verify` entrypoint and one allowlisted `python_quality` profile;
- runtime is expected to use `--pull=never`, `--network=none`, read-only rootfs, dropped capabilities and no-new-privileges;
- no credentials are accepted or forwarded;
- the image runs non-root by default and the dynamic verifier also overrides the container identity with the non-root host UID/GID;
- the profile refuses dependency, workflow and release-evidence mutations;
- compile, Ruff and portable regression checks execute only inside the isolated verifier container;
- PR builds do not publish packages;
- a merge to `main` publishes an exact-commit image to GHCR and uploads a provenance JSON artifact containing the exact published digest.

The published image digest is development evidence only. It does not satisfy Q10/Q11/Q12, does not become Q10 open-source layered security evidence and does not authorize production release or merge of PR #14.
