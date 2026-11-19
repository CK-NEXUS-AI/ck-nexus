# CK-NEXUS — DGX Spark AI Server Launch Brief

Status: Product launch / demonstration brief  
Event date: Friday, 4 September 2026  
Time: 13:00–17:00  
Venue: The Cloud  
Access: Invitation only

> This document records the product-launch scope and event plan. It is not Q10 certification evidence, does not change Q10/Q11/Q12 status, and must not be used to claim Production certification.

## Overview

CK-NEXUS is preparing an AI Server software experience for NVIDIA DGX Spark owners. The goal is to make local AI deployment, model lifecycle management, voice workflows, and automated video production easier to operate from one local-first environment.

The launch build is intended to help users install and maintain the software and driver stack required by current AI models, evaluate newly released models, and make selected models available for convenient local installation and use.

The system direction is local-first: model execution, voice workflows, and video-generation workflows are designed to run on the user's DGX Spark rather than depend on a remote inference service for the core processing path.

## 1. DGX Spark AI Server Manager

Primary responsibilities:

- Assist with DGX Spark software setup and maintenance.
- Track compatible driver, runtime, library, and model requirements.
- Help keep the local AI software stack ready for newer models.
- Curate newly released models for compatibility testing before presenting them to users.
- Provide a simpler model download/install/use workflow.
- Support multiple installed models and multi-model workflows where hardware/runtime constraints allow.
- Keep model/runtime state observable so users can see what is installed, ready, degraded, or unavailable.

### Design principles

- Local-first execution.
- Reuse installed components before downloading duplicates.
- Compatibility checks before upgrades.
- Rollback path for driver/runtime changes where practical.
- Explicit resource checks before loading multiple large models.
- No silent downgrade of security or isolation to make a model run.

## 2. Voice / TTS Studio

The launch scope includes a local voice workflow for creators and developers.

Planned capabilities:

- Train text-to-speech models using the user's own voice dataset.
- Manage voice datasets and training runs locally.
- Fast voice cloning for short-turnaround use cases.
- Preview generated speech before export/use.
- Keep source voice data and generated artifacts local by default.

### Safety / ownership boundary

Voice training and cloning should only be used with voices the user owns or has permission to use. Dataset provenance and consent should be recorded where the workflow is used beyond private experimentation.

## 3. AI Video Studio

The Video Studio is designed as an automated local production pipeline that starts from a concept and reference images.

Target workflow:

`Concept + Reference Images`
→ `Qwen: script / scene planning`
→ `FLUX: character sheet`
→ `Keyframe image generation`
→ `Qwen: concept / character / scene consistency review`
→ `LTX-2.5: multi-scene video generation`
→ `Local output / review`

### Workflow responsibilities

#### Qwen — Script and planning

- Convert the concept into a structured story/script.
- Break the story into scenes.
- Produce scene intent, shot requirements, character requirements, and prompt context.

#### FLUX — Character and visual references

- Generate character sheets from the approved concept/reference set.
- Produce visual references used by later scene/keyframe generation.

#### Keyframe stage

- Generate keyframe images for the planned scenes.
- Preserve character, visual identity, and scene intent as consistently as possible.

#### Qwen — Verification pass

Before video generation, review whether generated keyframes remain aligned with:

- Original concept.
- Character design.
- Scene description.
- Required visual continuity.

Frames that fail the declared criteria should be regenerated/reviewed rather than silently accepted.

#### LTX-2.5 — Multi-scene generation

- Build the final generation prompt from the approved scene plan and keyframes.
- Generate the sequence using a multi-scene prompt workflow.
- Keep the production path local on the DGX Spark.

## 4. Multi-model operation

The product direction supports workflows involving several models rather than assuming one model must perform every task.

Examples:

- Language/reasoning model for planning and review.
- Image model for character sheets and keyframes.
- Video model for multi-scene generation.
- TTS/voice models for dialogue or narration.

The runtime should account for VRAM/RAM/storage pressure and should not attempt to keep every large model resident simultaneously when the DGX Spark cannot safely support that configuration.

## 5. Launch event

### Event format

- Invitation only.
- Friday, 4 September 2026.
- 13:00–17:00.
- Venue: The Cloud.

### Audience

The event is intended for people who already own an NVIDIA DGX Spark and can attend in person.

### Launch offer

The program will be provided free to eligible DGX Spark owners who attend the launch event, subject to the final event distribution terms.

### Registration flow

Public call-to-action:

> DGX Spark owners who can attend should comment on the launch post. The registration URL will then be sent by direct message.

Do not publish a private registration URL in this repository unless it is explicitly intended to be public.

## 6. Release and verification boundary

This launch brief describes the intended product/demo scope. Individual capabilities must still be represented honestly according to their actual implementation and verification state.

Use separate states such as:

- `PLANNED`
- `IMPLEMENTED_NOT_VERIFIED`
- `VERIFIED_FOR_DEMO`
- `RELEASE_CANDIDATE`
- `PRODUCTION_VERIFIED`

A successful demonstration must not be treated as Q10 security certification or Production authorization.

## 7. Immediate implementation tracks

Recommended product tracks after the brief is accepted:

1. DGX Spark hardware/runtime inventory and compatibility detector.
2. Driver/runtime/model compatibility registry.
3. Model catalog + installation manager.
4. Resource-aware multi-model scheduler.
5. TTS dataset/training/quick-clone workflow.
6. Video Studio workflow state machine.
7. Qwen script and verification adapters.
8. FLUX character/keyframe adapter.
9. LTX-2.5 multi-scene adapter.
10. Local artifact library and run history.
11. Verification harness for each workflow stage.
12. Installer/update/rollback UX for DGX Spark owners.

## 8. Non-goals for this launch document

This document does not:

- certify Q10;
- unblock Q11 or Q12;
- authorize Production deployment;
- assert that every listed capability is already implemented;
- authorize paid APIs or cloud inference as a dependency;
- change frozen certification subjects.
