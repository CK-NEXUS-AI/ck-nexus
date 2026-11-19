# Evidence First

Use these statuses exactly:

DESIGNED
IMPLEMENTED
EXECUTED
VERIFIED
PRODUCTION

A higher status requires evidence for the lower status.

Required lineage:
REF -> COMMIT -> TREE -> SOURCE -> RELEASE -> APPLICATION

Required evidence fields where applicable:
- source_sha
- source_tree
- artifact_sha256
- command
- exit_code
- timestamp
- environment
- operator/actor
- verification_method

Never convert:
- documentation into implementation evidence;
- local test output into live evidence;
- dependency scan into deep security review;
- consensus into proof.
