# LangGraph Chat Agent

A lightweight FastAPI-based chat service built with **LangGraph**, **Gemini**, **PostgreSQL checkpointing**, **MCP**, and **A2A**.

The project provides a stateful chat agent that can:

* Maintain conversation history using LangGraph checkpoints.
* Automatically summarize long conversations.
* Use built-in tools for date/time and arithmetic.
* Connect to external MCP servers.
* Delegate tasks to external A2A agents.
* Pass request-specific context, such as timezone, into tools.
* Expose the agent through a simple FastAPI `/chat` API.

## Architecture

```text
                         ┌─────────────────────┐
                         │      Chat Client     │
                         └──────────┬──────────┘
                                    │
                                    │ POST /chat
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Agent         │
                         │                     │
                         │     LangGraph       │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             ┌────────────┐ ┌─────────────┐ ┌──────────────┐
             │ Gemini LLM │ │ Local Tools │ │ MCP / A2A    │
             └────────────┘ └─────────────┘ └──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ PostgreSQL          │
                         │ LangGraph           │
                         │ Checkpointer        │
                         └─────────────────────┘
```

## Features

### Stateful Conversations

Every request includes a `thread_id`.

LangGraph uses this ID to persist and restore the conversation state from PostgreSQL.

```json
{
  "timezone": "Asia/Kolkata",
  "message": "What did we talk about earlier?",
  "thread_id": "conversation-123"
}
```

Requests using the same `thread_id` continue the same conversation.

### Conversation Summarization

The graph uses `SummarizationNode` to automatically summarize long conversations.

```text
START
  │
  ▼
Agent
  │
  ▼
Summarize
  │
  ▼
 END
```

This allows conversations to grow without continuously sending the entire raw conversation history to the model.

### Tool Calling

The agent includes several built-in tools:

* `current_datetime`
* `add`
* `subtract`
* `multiply`
* `divide`

The `current_datetime` tool receives the request timezone through LangGraph runtime context.

For example:

```text
timezone = Asia/Kolkata
```

The tool returns the current time formatted for that timezone.

### MCP Support

The agent can connect to external MCP servers through `MultiServerMCPClient`.

Example:

```python
mcp = MultiServerMCPClient(
    {
        "weather_service": {
            "transport": "streamable_http",
            "url": "http://localhost:4055/mcp",
        },
    }
)
```

MCP tools are dynamically loaded during agent setup and added to the agent's tool list.

### A2A Support

The agent can also delegate work to external A2A agents.

Pass A2A server URLs when creating the agent:

```python
agent = Agent(
    key=config.gemini,
    a2a=[
        "http://localhost:4052",
    ],
)
```

The agent:

1. Fetches the remote agent card.
2. Reads its name, description, skills, tags, and examples.
3. Creates a LangChain tool representing the remote agent.
4. Allows Gemini to decide when to delegate work.
5. Sends the request to the remote A2A agent.

Conceptually:

```text
                     ┌─────────────────┐
                     │  Chat Agent     │
                     └────────┬────────┘
                              │
                         Tool Call
                              │
                              ▼
                     ┌─────────────────┐
                     │   A2A Agent     │
                     └─────────────────┘
```

## Project Structure

A simple project layout is:

```text
.
├── agent.py
├── main.py
├── tools.py
├── config.py
├── app.json
├── requirements.txt
└── README.md
```

### `main.py`

Creates the FastAPI application and manages the application lifecycle.

It initializes the PostgreSQL checkpointer and sets up the agent when the application starts.

### `agent.py`

Contains the LangGraph agent implementation.

Responsibilities include:

* Creating the Gemini model.
* Loading MCP tools.
* Connecting to A2A agents.
* Creating the LangGraph graph.
* Configuring conversation summarization.
* Invoking the graph.
* Cleaning up HTTP/A2A clients.

### `tools.py`

Contains the tools available to the agent.

It also defines the runtime context:

```python
@dataclass
class Context:
    timezone: ZoneInfo
```

### `config.py`

Loads application configuration from `app.json`.

Example:

```json
{
  "postgres": "postgresql://postgres:postgres@localhost:5432/postgres",
  "gemini": "YOUR_GEMINI_API_KEY"
}
```

## Requirements

* Python 3.11+
* PostgreSQL
* Google Gemini API key

The project uses:

* FastAPI
* Uvicorn
* LangGraph
* LangChain
* Gemini
* LangMem
* PostgreSQL
* MCP
* A2A
* HTTPX

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create `app.json` in the project root:

```json
{
  "postgres": "postgresql://postgres:postgres@localhost:5432/postgres",
  "gemini": "YOUR_GEMINI_API_KEY"
}
```

### PostgreSQL

The PostgreSQL database is used by `AsyncPostgresSaver` to persist LangGraph checkpoints.

Example connection string:

```text
postgresql://postgres:postgres@localhost:5432/postgres
```

The checkpointer is initialized during application startup:

```python
async with AsyncPostgresSaver.from_conn_string(config.postgres) as checkpointer:
    await checkpointer.setup()
    await agent.setup(checkpointer=checkpointer)
```

## Running the Server

Start the application with:

```bash
python main.py
```

The server runs on:

```text
http://localhost:3000
```

You can also run it directly with Uvicorn:

```bash
uvicorn main:app --port 3000
```

## API

### `GET /`

Health/root endpoint.

```bash
curl http://localhost:3000/
```

### `POST /chat`

Send a message to the agent.

Request:

```json
{
  "timezone": "Asia/Kolkata",
  "message": "What time is it?",
  "thread_id": "conversation-123"
}
```

Example:

```bash
curl -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "timezone": "Asia/Kolkata",
    "message": "What time is it?",
    "thread_id": "conversation-123"
  }'
```

Response:

```json
{
  "message": "2026-08-17T04:43:00+05:30"
}
```

## Timezone Context

The API accepts an IANA timezone:

```json
{
  "timezone": "Asia/Kolkata"
}
```

Other examples:

```text
Asia/Tokyo
America/New_York
Europe/London
Australia/Sydney
UTC
```

The timezone is converted into a `ZoneInfo` object and passed into the LangGraph runtime context:

```python
context=Context(
    timezone=timezone
)
```

The `current_datetime` tool can then access it through `ToolRuntime`.

## LangGraph Flow

The graph is intentionally simple:

```text
        ┌─────────┐
        │  START  │
        └────┬────┘
             │
             ▼
      ┌─────────────┐
      │    Agent    │
      │ Gemini +    │
      │ Tools       │
      └──────┬──────┘
             │
             ▼
      ┌─────────────┐
      │ Summarize   │
      │ Conversation│
      └──────┬──────┘
             │
             ▼
        ┌─────────┐
        │   END   │
        └─────────┘
```

The agent node is responsible for reasoning and tool calls.

The summarization node keeps the conversation within a manageable context window.

## Lifecycle

The FastAPI lifespan manages resources that need initialization and cleanup.

```text
Application Start
       │
       ▼
Create PostgreSQL Checkpointer
       │
       ▼
Initialize Database
       │
       ▼
Setup Agent
       │
       ▼
Serve Requests
       │
       ▼
Application Shutdown
       │
       ▼
Close A2A Clients
       │
       ▼
Close HTTP Client
```

This keeps long-lived resources such as the PostgreSQL checkpointer and A2A HTTP clients tied to the application lifecycle.

## Extending the Agent

### Add a Tool

Create a LangChain tool in `tools.py`:

```python
@tool
def my_tool(value: str) -> str:
    """Describe what this tool does."""
    return value
```

Then add it to the agent:

```python
_tools = [
    current_datetime,
    add,
    subtract,
    multiply,
    divide,
    my_tool,
]
```

### Add an MCP Server

Configure an MCP server when creating the agent:

```python
agent = Agent(
    key=config.gemini,
    mcp=MultiServerMCPClient(
        {
            "weather_service": {
                "transport": "streamable_http",
                "url": "http://localhost:4055/mcp",
            },
        }
    ),
)
```

The MCP tools will be discovered during `agent.setup()`.

### Add an A2A Agent

```python
agent = Agent(
    key=config.gemini,
    a2a=[
        "http://localhost:4052",
        "http://localhost:4053",
    ],
)
```

Each A2A server is discovered through its agent card and exposed to Gemini as a tool.

## Design Goals

The project intentionally keeps the orchestration layer small:

* **FastAPI** handles HTTP.
* **LangGraph** handles stateful agent execution.
* **Gemini** provides the LLM.
* **PostgreSQL** provides durable checkpoints.
* **MCP** provides external tools.
* **A2A** provides agent-to-agent delegation.
* **LangMem** handles conversation summarization.

This makes the application suitable as a small **chat orchestration service** that can sit between a Chat UI and a collection of tools and specialized agents.

## License

See [LICENSE](LICENSE).
