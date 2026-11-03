# Coding Agent

A terminal coding agent in Python, in the spirit of Claude Code. It chats with any
OpenAI-compatible model (OpenRouter by default), and can read, write and edit files,
run shell commands, search the web, and delegate to read-only sub-agents. Shell
commands and file writes go through an approval layer first.

## Requirements

- Python 3.10+
- An API key for an OpenAI-compatible endpoint (e.g. [OpenRouter](https://openrouter.ai))

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install openai pydantic click rich tomli platformdirs httpx tiktoken ddgs fastmcp
```

## Quick start

Set your credentials as environment variables:

```powershell
# PowerShell
$env:API_KEY  = "sk-or-..."
$env:BASE_URL = "https://openrouter.ai/api/v1"
```

```bash
# bash
export API_KEY="sk-or-..."
export BASE_URL="https://openrouter.ai/api/v1"
```

Then run:

```bash
python main.py                          # interactive session
python main.py --cwd path/to/project    # work on another directory
python main.py "explain main.py"        # single prompt, then exit
```

In interactive mode, type your request at the `>` prompt. `Ctrl+C` interrupts the
current input; `Ctrl+Z` then Enter (Windows) or `Ctrl+D` (macOS/Linux) exits.

> **Note:** single-prompt mode has no approval prompt — anything that would normally
> ask for confirmation is approved automatically. Use interactive mode for anything
> that changes files or runs commands.

## Tools

| Tool | Kind | What it does |
|---|---|---|
| `read_file` | read | Read a file with line numbers (supports `offset` / `limit`) |
| `write_file` | write | Create or overwrite a file |
| `edit` | write | Replace a string in a file (optionally all occurrences) |
| `shell` | shell | Run a command (`cmd.exe` on Windows, `bash` elsewhere), 120 s default timeout |
| `list_dir` | read | List a directory |
| `grep` | read | Regex search across files |
| `glob` | read | Find files by pattern |
| `web_search` | network | DuckDuckGo search |
| `web_fetch` | network | Fetch a URL as text |
| `todos` | memory | Session todo list (`add`, `complete`, `list`, `clear`) |
| `memory` | memory | Persistent key/value notes about the user, loaded into every session |
| `subagent_codebase_investigator` | — | Read-only sub-agent for exploring code (20 turns, 10 min) |
| `subagent_code_reviewer` | — | Read-only sub-agent for reviewing code (10 turns, 5 min) |

Tool output over 100 KB is truncated. In long sessions, old tool outputs are replaced
with a placeholder to save context.

## Approval and safety

Every tool that changes something (write, shell, network, memory) goes through
`safety/approval.py`. The behaviour depends on the `approval` setting:

| Policy | Behaviour |
|---|---|
| `on-request` *(default)* | Auto-approves read-only shell commands (`ls`, `git status`, `grep` …), new files and edits inside the project. Asks before other shell commands, overwriting existing files, and writing outside the project. |
| `auto-edut` | Same as `on-request` for shell commands. *(The value really is spelled `auto-edut` — see Known issues.)* |
| `auto` / `on-failure` | Approves everything except dangerous commands. |
| `never` | Approves only read-only shell commands; rejects everything else without asking. |
| `yolo` | Approves everything, including dangerous commands. |

Under every policy except `yolo`, these are **always rejected**: recursive deletes of
`/`, `~` or whole drives (`rm -rf /`, `del /s`, `rd /s`, `Remove-Item -Recurse`),
disk tools (`mkfs`, `fdisk`, `dd`, `format C:`), shutdown/reboot, `curl … | sh`, and
fork bombs.

A command only counts as read-only if it contains no chaining, piping, redirection
or substitution (`;` `&` `|` `<` `>` `` ` `` `$(`), so `ls && rm -rf src` is not
auto-approved.

Environment variables matching `*KEY*`, `*TOKEN*` or `*SECRET*` are removed before
shell commands run, so the agent cannot read your API key through the shell.

## Configuration

Settings are read from TOML files and merged, later files overriding earlier ones:

1. **User config:** `config.toml` in the platform config directory for `CLAUDECODE`
   (on Windows: `%LOCALAPPDATA%\CLAUDECODE\CLAUDECODE\config.toml`)
2. **Project config:** `.claudeclone/config.toml` in the working directory

If the working directory contains an `AGENT.MD` file, its contents are added to the
system prompt as project instructions (unless `developer_instructions` is set in config).

Example `config.toml`:

```toml
max_turns = 90                 # tool-calling rounds per request
approval = "on-request"
# allowed_tools = ["read_file", "grep", "glob", "list_dir"]   # optional allowlist
developer_instructions = "Prefer small, focused commits."
user_instructions = "Answer briefly."
hooks_enabled = true

[model]
name = "poolside/laguna-xs-2.1:free"
context_window = 256000

[shell_environment]
exclude_patterns = ["*KEY*", "*TOKEN*", "*SECRET*"]
set_vars = { PYTHONIOENCODING = "utf-8" }

[[hooks]]
name = "lint-after-edit"
trigger = "after_tool"         # before_agent | after_agent | before_tool | after_tool
command = "ruff check ."
timeout_sec = 30
```

### Hooks

A hook runs a shell `command` (or an inline bash `script`) at a point in the agent
loop. It receives context through environment variables:

| Variable | Set for |
|---|---|
| `AI_AGENT_TRIGGER`, `AI_AGENT_CWD` | all hooks |
| `AI_AGENT_USER_MESSAGE` | `before_agent`, `after_agent` |
| `AI_AGENT_RESPONSE` | `after_agent` |
| `AI_AGENT_TOOL_NAME`, `AI_AGENT_TOOL_PARAMS` | `before_tool`, `after_tool` |
| `AI_AGENT_TOOL_RESULT` | `after_tool` |

Hook output is discarded and failures do not stop the agent. Inline `script` hooks
need bash, so on Windows use `command` instead.

### Custom tools

Drop a Python file into `.ai-agent/tools/` in your project (or in the user config
directory). Every `Tool` subclass in it is registered at startup:

```python
from pydantic import BaseModel, Field
from tool.base import Tool, ToolInvocation, ToolKind, ToolResult


class EchoParams(BaseModel):
    message: str = Field(..., description="Text to echo back")


class EchoTool(Tool):
    name = "echo"
    description = "Echo a message back"
    kind = ToolKind.READ
    schema = EchoParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = EchoParams(**invocation.params)
        return ToolResult.success_result(params.message)
```

### Memory

The `memory` tool stores notes in `user_memory.json` in the platform data directory
for `claudeclone` (on Windows: `%LOCALAPPDATA%\claudeclone\claudeclone\`). They are
added to the system prompt at the start of every session.

## Project structure

```
main.py               CLI entry point (click) and event rendering
agent/
  agent.py            Agent loop: stream model output, run tool calls, repeat
  session.py          Wires together client, tools, context, approval, hooks
  agentevent.py       Events emitted to the UI
client/
  llm_client.py       OpenAI-compatible streaming client with retry/backoff
  response.py         Stream event and token-usage types
context/
  manager.py          Message history and pruning of old tool output
  compaction.py       Summarises the conversation when context fills up
prompt/systemprompt.py  System prompt builder
tool/
  base.py             Tool base class, results, diffs, confirmations
  registry.py         Tool registry; validation, approval and hooks per call
  builtin/            Built-in tools
  subagent.py         Sub-agent tools
  tooldiscovery.py    Loads custom tools from .ai-agent/tools/
  mcp/                MCP client (not yet wired up — see below)
safety/approval.py    Approval policies and command safety rules
hooks/hook_system.py  Hook runner
config/               Config model and TOML loader
ui/tui.py             Rich-based terminal UI
utils/                Path, text and error helpers
```

## Known issues

- **Single-prompt mode never asks for approval** (see Quick start).
- **Context compaction never runs.** Token usage from the model is not recorded, so
  the 80 % context threshold is never reached. Long sessions will eventually hit the
  model's context limit.
- **MCP servers are not connected.** The `mcp_servers` config and `tool/mcp/` code
  exist, but nothing starts them.
- **The commands in the welcome banner** (`/help`, `/config`, `/approval`, `/model`,
  `/exit`) are not implemented — they are sent to the model as ordinary messages.
- **Config folder names don't match each other** (`CLAUDECODE`, `.claudeclone`,
  `.ai-agent`). The `.CLAUDECODE/` folder in this repo is not read by anything.
- `config.temperature` returns the model name, and temperature is never sent to the API.
- The `auto-edit` approval policy is spelled `auto-edut` in code.
- The `on_error` hook trigger is never fired.
- Redirecting output to a file on Windows can crash with `UnicodeEncodeError`; set
  `PYTHONIOENCODING=utf-8` to avoid it.
