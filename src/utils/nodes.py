from dotenv import load_dotenv

from langchain.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from utils.models import llm
from utils.objects import Perspectives, as_analyst
from utils.prompts import analyst_instructions, question_instructions
from utils.states import GenerateAnalystState, InterviewState

load_dotenv()


def create_analysts(state: GenerateAnalystState):
    """Create analysts"""

    topic = state["topic"]
    max_analysts = state["max_analysts"]
    human_analyst_feedback = state.get("human_analyst_feedback") or "No feedback provided."
    structured_llm = llm.with_structured_output(Perspectives)
    system_message = analyst_instructions.format(topic=topic,
                                                 human_analyst_feedback=human_analyst_feedback,
                                                 max_analysts=max_analysts)
    result = structured_llm.invoke([SystemMessage(content=system_message), HumanMessage(content="please generate the set of analysts.")])

    return {"analysts": result.analysts}


def human_feedback(state: GenerateAnalystState):
    """this is where the human gives a feedback about the analysts given"""
    feedback = interrupt({
        "question": "Are these analysts okay for you ? ",
        "analysts": [
            analyst.model_dump() if hasattr(analyst, "model_dump") else analyst
            for analyst in state.get("analysts", [])
        ],
        "instructions": "Return feedback to regenerate analysts or return empty/perfect/continue/okay to approve and continue the graph"
    })
    if feedback is None:
        return {"human_analyst_feedback": None}
    if isinstance(feedback, str):
        feedback = feedback.strip()

        if feedback == "":
            return {"human_analyst_feedback": None}
        if feedback.lower() in {"perfect", 'okay', "continue", "yes"}:
            return {"human_analyst_feedback": None}

        return {"human_analyst_feedback": feedback}

    return {"human_analyst_feedback": None}


def generate_question(state: InterviewState):
    """ask_question node: the analyst asks the next question to the expert"""
    analyst = as_analyst(state["analyst"])
    system_message = question_instructions.format(goals=analyst.persona)
    question = llm.invoke([SystemMessage(content=system_message), *state["messages"]])

    return {"messages": [question]}
