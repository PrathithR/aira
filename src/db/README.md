# Database Layer

The Database layer is the source of truth for AIRA.

## Responsibilities

- Define ORM models
- Create database sessions
- Handle migrations (future)
- Store OAuth tokens (encrypted)
- Store tasks, chat history, preferences
- Enforce user isolation (Phase 3)

## Non-Responsibilities

The DB layer must NOT:

- Contain business logic
- Know about LLM providers
- Call external APIs

All database writes must pass through validated application logic.
