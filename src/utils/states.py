import operator
from typing import Annotated, List, Optional

from langgraph.graph import MessagesState
from typing_extensions import NotRequired, TypedDict

from utils.objects import Analyst


class GenerateAnalystState(TypedDict):
    """State of the analyst-creation graph (phase 1)."""

    topic: str
    max_analysts: int
    human_analyst_feedback: NotRequired[Optional[str]]
    analysts: NotRequired[List[Analyst]]


class InterviewState(MessagesState):
    """State of one interview with one expert (inner subgraph)."""

    max_num_turns: int
    context: Annotated[list, operator.add]
    analyst: Analyst
    interview: str
    # fan-in back to the parent graph: one entry per interview
    interviews: Annotated[list, operator.add]


class ResearchGraphState(TypedDict):
    """State of the full research graph (outer graph)."""

    topic: str
    max_analysts: int
    human_analyst_feedback: NotRequired[Optional[str]]
    analysts: NotRequired[List[Analyst]]
    interviews: NotRequired[Annotated[list, operator.add]]
    sections: NotRequired[Annotated[list, operator.add]]
    introduction: NotRequired[str]
    content: NotRequired[str]
    conclusion: NotRequired[str]
    final_report: NotRequired[str]
