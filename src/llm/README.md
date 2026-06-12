# LLM Layer Reference Documentation

## 1. Purpose
This layer acts as a thin, stateless wrapper over LiteLLM. Its sole responsibility is to take an already-assembled list of messages (and optional tool definitions), make exactly one asynchronous call to the target language model, and return a normalized, vendor-agnostic response object. It deliberately does not handle ReAct agent loops, prompt engineering, tool execution, or database access.

## 2. Public Surface
The following public symbols are exposed from the `src.llm` namespace:
- `complete`: The main entry-point function for completing a chat.
- `LLMResponse`: The unified completion response returned by the layer.
- `ToolCall`: Standardized model-requested tool calls.
- `Usage`: Token usage information.
- `Message`: Type-hinted dictionary representing a chat message.
- `Role`: Supported chat participant roles.
- `LLMError`: The parent exception class for all LLM errors.
- `LLMTimeoutError`: Exception representing request timeout failures.
- `LLMAuthError`: Exception representing API authentication failures.
- `LLMRateLimitError`: Exception representing rate-limit exhaustion.

## 3. File Index & Reference

### `__init__.py`
**Purpose:** Re-exports the public interface elements of the LLM wrapper package.  
**Public:** `complete`, `LLMResponse`, `ToolCall`, `Usage`, `Message`, `Role`, `LLMError`, `LLMTimeoutError`, `LLMAuthError`, `LLMRateLimitError`.  
**Private:** None.

### `client.py`
**Purpose:** Formulates LLM request parameters, triggers async completions using LiteLLM, and maps the responses and exceptions.  
**Public:** `complete`.  
**Private:** `_build_request`, `_to_response`.

| Method | Signature | Returns | Raises | Called by | Calls |
|---|---|---|---|---|---|
| `complete` | `async def complete(messages: list[Message], tools: list[dict] \| None = None, *, model: str \| None = None, temperature: float \| None = None, max_tokens: int \| None = None) -> LLMResponse` | `LLMResponse` | `LLMError`, `LLMTimeoutError`, `LLMAuthError`, `LLMRateLimitError` | Agent layer | `_build_request`, `litellm.acompletion`, `_to_response` |
| `_build_request` | `def _build_request(messages: list[Message], tools: list[dict] \| None, model: str \| None, temperature: float \| None, max_tokens: int \| None) -> dict[str, Any]` | `dict[str, Any]` | — (internal helper) | `complete` | reads `settings` values |
| `_to_response` | `def _to_response(raw: Any) -> LLMResponse` | `LLMResponse` | — (internal helper) | `complete` | `json.loads` |

### `types.py`
**Purpose:** Holds all dataclasses, literals, and TypedDict configurations for inputs and outputs.  
**Public:** `Role`, `Message`, `ToolCall`, `Usage`, `LLMResponse`.  
**Private:** None.

#### `Message` (TypedDict)
| Field | Type | Meaning | Optional? |
|---|---|---|---|
| `role` | `Role` | Participant role (`"system"`, `"user"`, `"assistant"`, `"tool"`) | No (Required) |
| `content` | `str \| None` | Text content of the message | Yes (default None) |
| `tool_calls` | `list[dict]` | List of tool calls requested by assistant turn | Yes |
| `tool_call_id` | `str` | Matching target tool call ID for result turn | Yes |
| `name` | `str` | Name of the tool or entity | Yes |

#### `ToolCall` (Dataclass)
| Field | Type | Meaning | Optional? |
|---|---|---|---|
| `id` | `str` | The unique identifier of the tool call | No |
| `name` | `str` | The name of the tool requested | No |
| `arguments` | `dict` | Pre-parsed arguments dictionary (parsed from JSON) | No |

#### `Usage` (Dataclass)
| Field | Type | Meaning | Optional? |
|---|---|---|---|
| `prompt_tokens` | `int` | Input token count | No |
| `completion_tokens` | `int` | Output token count | No |
| `total_tokens` | `int` | Combined token count | No |

#### `LLMResponse` (Dataclass)
| Field | Type | Meaning | Optional? |
|---|---|---|---|
| `text` | `str \| None` | Text response returned by the model | No |
| `tool_calls` | `list[ToolCall]` | Parsed list of tool calls requested | No (defaults to empty list) |
| `finish_reason` | `str` | Reason returned by the model for termination | No (defaults to `""`) |
| `usage` | `Usage \| None` | Extracted usage metadata, if returned | No (defaults to `None`) |

### `errors.py`
**Purpose:** Contains the custom exceptions hierarchy that shields external layers from LiteLLM exceptions.  
**Public:** `LLMError`, `LLMTimeoutError`, `LLMAuthError`, `LLMRateLimitError`.  
**Private:** None.

| Exception Class | Parent Class | Trigger Condition |
|---|---|---|
| `LLMError` | `Exception` | Generic fallback exception for execution failures |
| `LLMTimeoutError` | `LLMError` | Triggers on requests exceeding network/timeout limits |
| `LLMAuthError` | `LLMError` | Triggers on missing or invalid API keys |
| `LLMRateLimitError` | `LLMError` | Triggers on rate limit exhaustion or resource exhaustion |

## 4. The Contract
The primary interface that other modules (primarily the Agent) rely on is the `complete()` function:
```python
async def complete(
    messages: list[Message],
    tools: list[dict] | None = None,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LLMResponse:
```

## 5. Settings Consumed
The LLM layer reads configurations from the `src.settings.settings` singleton:
| Setting | Use |
|---|---|
| `llm_provider` | Used to detect if Ollama is selected (`== "ollama"`) |
| `llm_model` | The default model string identifier passed to LiteLLM |
| `llm_temperature` | The default temperature value for generation |
| `llm_max_tokens` | The default token limit for completions |
| `active_api_key` | Retrieves the API key for the selected provider (raises if missing; returns `""` for Ollama) |
| `ollama_base_url` | Configures the `api_base` when calling local Ollama |
| `log_llm_responses` | Configures whether responses are logged as debug entries |

## 6. Usage Example
Below is an example of an agent invoking the LLM layer:
```python
from src.llm import complete, Message

messages: list[Message] = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the weather like in Seattle?"}
]

response = await complete(messages)
if response.has_tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool request: {tool_call.name} with arguments {tool_call.arguments}")
else:
    print(f"Assistant replied: {response.text}")
```

## 7. Extension Points
Should additional capabilities be required, the following guidelines apply:
- **Streaming Support**: Add an async generator function `stream()` alongside `complete()`.
- **Cost Tracking**: Extend `_to_response` to check model databases and calculate monetary costs under `LLMResponse.usage`.
- **Custom Factories**: If provider divergences occur, they should be implemented inside `client.py` private helpers (`_build_request` or `_to_response`), keeping the outer contract signature stable.
