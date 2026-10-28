from typing import List, Optional

from typing_extensions import NotRequired, TypedDict

from utils.objects import Analyst


class GenerateAnalystState(TypedDict):
    topic: str
    max_analysts: int
    human_analyst_feedback: NotRequired[Optional[str]]
    analysts: NotRequired[List[Analyst]]
