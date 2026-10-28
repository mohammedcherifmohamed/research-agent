from  dotenv import load_dotenv
from utils.states import GenerateAnalystState
from utils.models import llm
from utils.objects import Analyst,Perspectives
from utils.prompts import analyst_instructions
from langchain.messages import SystemMessage , HumanMessage
from langgraph.types import interrupt

load_dotenv()


def create_analysts(state: GenerateAnalystState):
    """Create analysts"""

    topic = state["topic"] 
    max_analysts = state["max_analysts"]
    human_analyst_feedback = state.get("human_analyst_feedback") or "No feedback provided."
    structured_llm  = llm.with_structured_output(Perspectives)
    system_message = analyst_instructions.format(topic=topic,
                                                 human_analyst_feedback=human_analyst_feedback,
                                                 max_analysts=max_analysts)
    result = structured_llm.invoke([SystemMessage(content=system_message), HumanMessage(content="please generate the set of analysts.")])

    return {"analysts": result.analysts}

def human_feedback(state: GenerateAnalystState):
    """this is where the human gives a feedback about the analysts given"""
    feedback = interrupt({
        "question" : "Are these analysts okay for you ? ",
        "analysts" : [
            analyst.model_dump() if hasattr(analyst,"model_dump") else analyst 
             for analyst in state.get("analysts",[])
        ],
        "instructions":"Return feedback to regenerate analysts or return empty/perfect/continue/okay to approve and continue the graph"
    })
    if feedback is None: 
        return {"human_analyst_feedback": None}
    if isinstance(feedback,str):
        feedback = feedback.strip()

        if feedback == "" :
            return {"human_analyst_feedback":None}
        if feedback.lower() in {"perfect",'okay',"continue","yes"}:
            return {"human_analyst_feedback":None}
        
        return {"human_analyst_feedback":feedback}
    
    return {"human_analyst_feedback":None}
    
