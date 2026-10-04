# Production Rules

Production promotion requires explicit evidence.

Minimum distinction:
- candidate != production;
- configured != connected;
- connected != executed;
- executed != verified;
- verified != production unless promotion criteria are satisfied.

Production promotion is forbidden when a required gate is BLOCKED, NOT_VERIFIED, or evidence is stale for the target source.
