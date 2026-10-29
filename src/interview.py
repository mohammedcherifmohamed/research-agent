from langgraph.graph import START, END, StateGraph

from utils.edges import route_messages
from utils.interview_nodes import answer_question, save_interview, search_web, search_web2
from utils.nodes import generate_question
from utils.states import InterviewState


builder = StateGraph(InterviewState)

builder.add_node("ask_question", generate_question)
builder.add_node("search_web", search_web)
builder.add_node("search_web2", search_web2)
builder.add_node("answer_question", answer_question)
builder.add_node("save_interview", save_interview)

builder.add_edge(START, "ask_question")
builder.add_edge("ask_question", "search_web")
builder.add_edge("ask_question", "search_web2")
builder.add_edge("search_web", "answer_question")
builder.add_edge("search_web2", "answer_question")
builder.add_conditional_edges(
    "answer_question", route_messages, ["ask_question", "save_interview"]
)
builder.add_edge("save_interview", END)

interview_graph = builder.compile()
