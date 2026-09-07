from agent_app.agent import Agent


def test_echo_command() -> None:
    agent = Agent()
    assert agent.handle("echo hello") == "hello"


def test_help_command() -> None:
    agent = Agent()
    output = agent.handle("help")
    assert "Available tools" in output


def test_add_command() -> None:
    agent = Agent()
    assert agent.handle("add 2 3") == "5"


def test_unknown_command() -> None:
    agent = Agent()
    assert "Unknown command" in agent.handle("unknown")
