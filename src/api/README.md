# API Layer

The API layer is the network boundary of AIRA.

It exposes REST and WebSocket endpoints to clients (CLI, PWA, or future mobile apps).

## Responsibilities

- Authenticate incoming requests
- Validate request bodies (Pydantic schemas)
- Enforce authorization (user scoping)
- Call the Agent layer
- Stream or return responses to the client

## Non-Responsibilities

The API layer must NOT:

- Build prompts
- Call LiteLLM directly
- Execute tools
- Call external APIs (Google, Slack, etc.)
- Contain business logic

All reasoning lives in the Agent layer.

## Flow

Client → API → Agent → API → Client