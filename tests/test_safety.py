import pytest

from gui_agent.agent import AgentDecision
from gui_agent.runtime import ActionPolicy, UnsafeActionError


@pytest.mark.parametrize(
    "text",
    [
        "powershell",
        "cmd.exe /c echo test",
        "python -m gui_agent.runtime.cli",
        "python --m gui_agent.runtime.cli",
        "gui-agent-v1 --execute",
        "Start-Process msedge",
    ],
)
def test_policy_blocks_terminal_and_self_invocation(text) -> None:
    with pytest.raises(UnsafeActionError):
        ActionPolicy().validate(AgentDecision("type", parameters={"text": text}))


def test_policy_allows_gui_text_and_paths() -> None:
    policy = ActionPolicy()
    policy.validate(AgentDecision("type", parameters={"text": "GUI Agent 测试"}))
    policy.validate(
        AgentDecision(
            "type",
            parameters={"text": r"C:\Users\m1865\Desktop\GUI-agent\README.md"},
        )
    )


def test_policy_limits_text_length() -> None:
    with pytest.raises(UnsafeActionError, match="长度"):
        ActionPolicy(max_text_length=3).validate(AgentDecision("type", parameters={"text": "1234"}))


def test_policy_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="max_text_length"):
        ActionPolicy(max_text_length=0)


def test_policy_ignores_non_text_and_missing_text() -> None:
    policy = ActionPolicy()
    policy.validate(AgentDecision("click", parameters={"x": 50, "y": 50}))
    policy.validate(AgentDecision("type", parameters={}))


def test_policy_blocks_top_left_pointer_actions() -> None:
    with pytest.raises(UnsafeActionError, match="左上角"):
        ActionPolicy().validate(AgentDecision("context_open", parameters={"x": 10, "y": 10}))
