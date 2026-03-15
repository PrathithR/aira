# Services Layer

The Services layer contains integration logic.

It is responsible for communicating with external systems.

## Responsibilities

- Call external APIs (Google Calendar, Gmail, Slack, etc.)
- Encrypt and decrypt sensitive tokens
- Normalize API responses
- Handle API errors and retries
- Interact with the database

## Non-Responsibilities

Services must NOT:

- Contain LLM logic
- Build prompts
- Handle HTTP request/response objects

Services are pure integration modules.
