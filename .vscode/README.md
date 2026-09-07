# Agent App

A small Python agent starter project that runs locally without any external API key. It ships with a simple interactive prompt loop and a pluggable tool system that can be extended with more capabilities.

## Features

- Local prompt loop using Python standard library only
- Pluggable tool registry
- Built-in demo tools: help, echo, time, and add
- Ready to run as a module with `python -m agent_app`
- Includes basic pytest coverage

## Quick start

```bash
python -m pip install -r requirements.txt
python -m agent_app
```

When the prompt appears, try:

- `help`
- `echo hello`
- `time`
- `add 2 3`
- `exit`

## Project structure

```text
agent_app/
  __init__.py
  __main__.py
  agent.py
  tools.py
tests/
  test_agent.py
```

## Extending the agent

Add a new callable tool in `agent_app/tools.py` and register it in the `TOOL_REGISTRY` dictionary. The agent will automatically expose it through the interactive loop.
