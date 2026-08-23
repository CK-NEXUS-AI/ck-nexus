# Mobile Proof Benchmark V1

## Purpose

This protocol exists to replace design claims with measured evidence. It does not claim that CK-NEXUS or AGNES runs on a 4 GB Android device until a qualifying device run is captured and independently reviewed.

## Claim states

- TARGET: intended capability with no qualifying measurement.
- MEASURED_NOT_VERIFIED: a measurement exists but has not passed independent verification.
- VERIFIED: required evidence is complete and an independent verifier accepted the exact evidence subject.
- REJECTED: evidence contradicts the claim or the protocol was not satisfied.

Marketing and product documentation must not translate TARGET or MEASURED_NOT_VERIFIED into a completed capability.

## First claim under test

AGNES and the CK-NEXUS mobile runtime can execute a defined minimal workload on an Android device in the 4 GB RAM class without process termination and within the declared resource budget.

The current state of this claim is TARGET.

## Required device evidence

Record the following without secrets or personal data:

- Android version and API level.
- Device architecture.
- Physical memory reported by the operating system.
- Termux version and installation source where available.
- Repository commit and tree under test.
- Exact command and workload identifier.
- Model name, model file digest, quantization, context size, and model license when local inference is included.
- Wall-clock duration.
- Target process RSS or PSS measured outside the Python harness where the platform permits it.
- System available memory before and after.
- Exit status and whether Android killed or reclaimed the process.
- Output digest.
- Evidence file SHA-256.

## Workloads

Run each workload at least three times after one warm-up. Keep input fixed across candidates.

1. Core baseline: import and execute a deterministic CK-NEXUS or AGNES local code path without a model.
2. API baseline: start the local service, call health or a deterministic local endpoint, then stop it.
3. Local inference candidate: run the same fixed prompt through llama.cpp when a compatible GGUF model is available.
4. Integrated candidate: run the smallest AGNES path that invokes local inference without network access.

Ollama is not a required Android baseline unless an officially supported Android runtime is identified and pinned. Do not force an unfair comparison simply because Ollama is used on desktop systems.

## Pass criteria for the 4 GB claim

A candidate can become VERIFIED only when all of the following are true:

- The qualifying device reports no more than 4.5 GiB physical memory, allowing normal vendor reporting variance around a marketed 4 GB class device.
- All required workloads complete without process kill, crash, swap-induced test invalidation, or hidden cloud inference.
- Three measured runs are present for each required workload.
- Exact repository subject and model digest are recorded.
- Peak target-process memory is captured with a method whose limitations are documented.
- Median and worst-case latency are reported, not only the fastest run.
- Network-off integrated execution is separately demonstrated before making an offline claim.
- An independent verifier checks the evidence bundle and its SHA-256 digests.

Passing the core baseline alone proves only that the Python runtime path fits. It does not prove local-model or full offline capability.

## Measurement command

Use the repository harness to create a machine-readable record:

```text
python scripts/mobile_benchmark.py --output evidence/mobile/core-run-01.json --label core-run-01 -- python -m pytest -q <pinned-test>
```

For a local inference candidate, invoke the pinned llama.cpp binary and fixed model through the same harness. Capture target-process RSS or PSS separately because the harness deliberately does not pretend its own `ru_maxrss` is the child process memory measurement.

## Evidence bundle

Store only non-secret benchmark evidence. A final bundle should contain the JSON records, a manifest with SHA-256 digests, device metadata, exact subject identity, measurement-method notes, and verifier decision.

Do not commit model files, credentials, private device identifiers, raw user conversations, or access tokens.

## Interpretation rules

- No measurement means TARGET.
- A local run without independent review means MEASURED_NOT_VERIFIED.
- A successful desktop or VPS run cannot prove the Android claim.
- A Termux shell starting successfully cannot prove the AGNES claim.
- llama.cpp running successfully cannot by itself prove CK-NEXUS integration.
- Network-off execution must be tested explicitly; cached or previously downloaded artifacts are allowed only when declared.

## Research basis

The llama.cpp project documents Android execution through Termux and warns that context size can cause memory spikes. Termux documentation also records Android-specific process and `/proc` visibility restrictions. These references justify using llama.cpp as the first local inference candidate and justify recording measurement limitations instead of assuming desktop observability applies unchanged on Android.
