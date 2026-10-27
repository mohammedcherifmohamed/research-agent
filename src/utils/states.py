from typing_extensions import TypedDict,NotRequired

from typing import Optional , List
from utils.objects import Analyst

class  GenerateAnalystState(TypedDict) : 
    topic: str
    max_analysts:int
    humman_analyst_feedback: NotRequired[Optional[str]]
    analysts:NotRequired[List[analysts]]
    