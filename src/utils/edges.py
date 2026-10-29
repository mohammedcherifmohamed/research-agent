from typing import Literal

from langchain.messages import AIMessage
from langgraph.graph import END

from utils.messages import message_text
from utils.states import GenerateAnalystState, InterviewState


def should_continue(state: GenerateAnalystState) -> Literal["create_analysts", "__end__"]:
    """Regenerate the analysts if the human gave feedback, otherwise stop."""

    if state.get("human_analyst_feedback"):
        return "create_analysts"
    return END


THANKS = "Thank you so much for your help"


def route_messages(
    state: InterviewState, name: str = "expert"
) -> Literal["ask_question", "save_interview"]:
    """Decide whether the interview continues or is saved."""
    messages = state["messages"]
    max_num_turns = state.get("max_num_turns", 2)

    # number of expert answers so far
    num_responses = sum(
        1
        for message in messages
        if isinstance(message, AIMessage) and message.name == name and message_text(message)
    )
    if num_responses >= max_num_turns:
        return "save_interview"

    # messages[-1] is the expert's answer, messages[-2] the analyst's question
    last_question = messages[-2] if len(messages) >= 2 else messages[0]
    if THANKS in message_text(last_question):
        return "save_interview"

    return "ask_question"
