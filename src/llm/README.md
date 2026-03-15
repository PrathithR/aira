# LLM Layer

The LLM layer is a thin abstraction over LiteLLM.

It isolates model provider details from the Agent layer.

## Responsibilities

- Call LiteLLM
- Inject provider-specific configuration
- Handle API keys
- Return structured model responses

## Non-Responsibilities

The LLM layer must NOT:

- Execute tools
- Access the database
- Know about users
- Perform business logic

This layer exists to:

- Allow model switching via configuration
- Enable token usage tracking (Phase 3)
- Centralize retries and logging
- Simplify testing and mocking
