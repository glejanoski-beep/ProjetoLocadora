"""Core agent logic for prompt and routing."""

from __future__ import annotations

from typing import Callable

from .tools import TOOL_REGISTRY


class Agent:
    """A minimal interactive agent that dispatches commands to tools."""

    def __init__(self, tools: dict[str, Callable[..., str]] | None = None) -> None:
        self.tools = tools or TOOL_REGISTRY

    def handle(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return "Please enter a command."

        if text.lower() in {"exit", "quit"}:
            return "Goodbye!"

        parts = text.split()
        command = parts[0].lower()
        tool = self.tools.get(command)

        if tool is None:
            return f"Unknown command: {command}. Type 'help' for available tools."

        args = parts[1:]
        if command == "echo":
            return tool(" ".join(args))
        if command == "add":
            if len(args) != 2:
                return "Usage: add <number1> <number2>"
            return tool(args[0], args[1])
        if command == "help":
            return tool()
        if command == "time":
            return tool()

        return tool(*args)

    def run(self) -> None:
        print("Agent ready. Type 'help' or 'exit'.")
        while True:
            user_input = input("You> ")
            response = self.handle(user_input)
            print(f"Agent> {response}")
            if response == "Goodbye!":
                break
