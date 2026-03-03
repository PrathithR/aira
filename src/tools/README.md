# Tools Layer

Tools are LLM-facing wrappers around services.

Each tool:

- Has a clear name
- Has a precise description
- Defines a strict parameter schema
- Returns structured output

## Responsibilities

- Define tool metadata for the LLM
- Validate arguments from the LLM
- Call the appropriate service method
- Return normalized results

## Non-Responsibilities

Tools must NOT:

- Build prompts
- Access HTTP or API routes
- Contain complex business logic

Tools are the bridge between the Agent and Services layers.