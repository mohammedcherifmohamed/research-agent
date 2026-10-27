from  dotenv import load_dotenv
from utils.states import GenerateAnalystState
from utils.models import llm
from utils.objects import Analyst,Perspectives
from utils.prompts import analyst_instructions
from langchain.messages import SystemMessage , HumanMessage


load_dotenv()


def create_analysts(state: GenerateAnalystState):
    """Create analysts"""

    topic = state["topic"] 
    max_analysts = state["max_analysts"]
    human_analyst_feedback = state["humman_analyst_feedback"]
    structred_llm  = llm.with_structred_output(Perspectives)
    system_message = analyst_instructions.format(topic=topic,
                                                 human_analyst_feedback=human_analyst_feedback,
                                                 max_analysts=max_analysts)
    analysts = structred_llm.invoke([SystemMessage(cotnent=system_message)]+[HumanMessage(content="please generate the set of analysts.")])

    return {"analysts":Analyst.analysts}