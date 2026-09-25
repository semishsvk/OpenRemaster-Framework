# Architecture

## Isolation contract

OpenRemaster Framework is a sidecar. During Phase 1, OpenAzrael and OpenCadaver are external read-only inputs.

Adapters expose observations only. They intentionally have no commit, push, branch, checkout, write, delete, or source-tree mutation interface.

## Evidence identity

Evidence identity binds project ID, source revision, input digest, tool ID/version, and check ID. Dependency edges allow downstream evidence to be invalidated transitively.

## Adoption

Existing project orchestration remains authoritative. Future impact analysis is advisory/shadow-only until an explicit acceptance gate promotes it.
