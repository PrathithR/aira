# Agent Layer

The Agent layer orchestrates the decision loop.

It is the central reasoning controller of AIRA.

## Responsibilities

- Build prompt context (history + system instructions)
- Inject tool definitions
- Call the LLM via the llm/ layer
- Interpret tool calls
- Validate tool arguments
- Execute tools
- Feed results back to the LLM
- Enforce max iteration limits
- Return final structured response

## Non-Responsibilities

The Agent layer must NOT:

- Talk to HTTP or WebSockets
- Call external APIs directly
- Write to the database without validation
- Handle authentication

The Agent enforces boundaries between LLM decisions and real-world side effects.

## Loop Model

Send → Receive → Execute Tool → Feed Back → Repeat → Final Response