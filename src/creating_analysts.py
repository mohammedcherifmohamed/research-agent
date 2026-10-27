from utils.nodes import create_analysts 
from langgraph.graph import START,END , StateGraph

from utils.states import GenerateAnalystState
from dotenv import load_dotenv


load_dotenv()


builder = StateGraph(GenerateAnalystState)


builder.add_node(START,"create_analysts")
builder.add_node("create_analysts",END)

graph = builder.compile()

  