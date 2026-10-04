# CK-NEXUS Governed AI Development System

Status: DESIGN + IMPLEMENTATION BASELINE

This document defines the Category A canonical development system. It does not by itself prove runtime or production status.

## Five canonical layers

1. Developer Context: CLAUDE.md and scoped rules.
2. Reusable Intelligence: skills and operational knowledge.
3. Governed Agents: agents/subagents, MCP/tools and authority boundaries.
4. Controlled Execution: Policy Kernel, Execution Gateway and Sandbox/runtime.
5. Proof System: Verification, Evidence and execution lineage.

## Core invariant

Agent proposes. Policy decides. Gateway executes. Verifier proves. Evidence records.

## Canonical execution lineage

Human Intent -> Agent Identity -> Lease -> Policy -> Approval -> Credential Reference -> Sandbox -> Execution -> Verification -> Evidence -> Memory -> Learning/Recovery

## Capability model

Evaluate agentic systems by capability rather than a vendor-specific level: intent handling, planning, state/memory, tool use, multi-step execution, recovery, multi-agent coordination, policy enforcement, verification and evidence.

## Implementation boundary

React, Vue, Node, Express, PostgreSQL, SQLite and similar technologies are implementation choices, not CK-NEXUS invariants unless separately recorded.

## Evidence boundary

Research can establish DESIGNED findings. Code can establish IMPLEMENTED only after the change exists. A command run establishes EXECUTED. Independent reproduction establishes VERIFIED. Production requires explicit production evidence and promotion criteria.
