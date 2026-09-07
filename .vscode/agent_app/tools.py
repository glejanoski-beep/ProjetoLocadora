"""Tool implementations for the local agent."""

from __future__ import annotations

from datetime import datetime
from typing import Callable


class ToolRegistry(dict):
    """A simple registry of callable tools."""

    def register(self, name: str, func: Callable[..., str]) -> None:
        self[name] = func

    def get_tool_names(self) -> list[str]:
        return sorted(self.keys())


def help_tool() -> str:
    """Return a summary of available commands."""
    return (
        "Available tools: help, echo, time, add.\n"
        "Try: help, echo hello, time, add 2 3"
    )


def echo_tool(message: str) -> str:
    return message


def time_tool() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_tool(a: str, b: str) -> str:
    try:
        total = int(a) + int(b)
        return str(total)
    except ValueError:
        return "Please provide integer values for add."


TOOL_REGISTRY = ToolRegistry()
TOOL_REGISTRY.register("help", help_tool)
TOOL_REGISTRY.register("echo", echo_tool)
TOOL_REGISTRY.register("time", time_tool)
TOOL_REGISTRY.register("add", add_tool)
