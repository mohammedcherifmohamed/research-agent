from dotenv import load_dotenv
from langgraph.graph import START, END, StateGraph

from utils.edges import should_continue
from utils.nodes import create_analysts, human_feedback
from utils.states import GenerateAnalystState

load_dotenv()


builder = StateGraph(GenerateAnalystState)

builder.add_node("create_analysts", create_analysts)
builder.add_node("human_feedback", human_feedback)

builder.add_edge(START, "create_analysts")
builder.add_edge("create_analysts", "human_feedback")
builder.add_conditional_edges("human_feedback", should_continue, ["create_analysts", END])

graph = builder.compile()
