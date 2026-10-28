from typing import Literal

from langgraph.graph import END

from utils.states import GenerateAnalystState


def should_continue(state: GenerateAnalystState) -> Literal["create_analysts", "__end__"]:
    """Regenerate the analysts if the human gave feedback, otherwise stop."""

    if state.get("human_analyst_feedback"):
        return "create_analysts"
    return END
