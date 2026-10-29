"""Nodes of the interview subgraph (one interview = one analyst × one expert)."""

from langchain.messages import SystemMessage

from utils.messages import format_transcript
from utils.models import llm
from utils.objects import Queries, SearchQuery, as_analyst
from utils.prompts import answer_instructions, search_instructions
from utils.states import InterviewState
from utils.tools import format_docs, run_search, tavily_search, tavily_search_2


def _rewrite_query(state: InterviewState, schema) -> list[str]:
    """Turn the conversation into web search queries."""
    structured_llm = llm.with_structured_output(schema)
    result = structured_llm.invoke(
        [SystemMessage(content=search_instructions), *state["messages"]]
    )
    return list(result.queries) if isinstance(result, Queries) else [result.search_query]


def search_web(state: InterviewState):
    """search_web node: one query, cheap search."""
    query = _rewrite_query(state, SearchQuery)[0]

    return {"context": run_search(tavily_search, query)}


def search_web2(state: InterviewState):
    """search_web2 node: several queries, deeper search, de-duplicated by URL."""
    queries = _rewrite_query(state, Queries)

    docs: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        for doc in run_search(tavily_search_2, query):
            key = doc["url"] or doc["content"][:80]
            if key in seen:
                continue
            seen.add(key)
            docs.append(doc)

    return {"context": docs}


def answer_question(state: InterviewState):
    """answer_question node: the expert answers using the retrieved context."""
    analyst = as_analyst(state["analyst"])
    context = format_docs(state["context"])
    system_message = answer_instructions.format(goals=analyst.persona, context=context)

    answer = llm.invoke([SystemMessage(content=system_message), *state["messages"]])
    answer.name = "expert"

    return {"messages": [answer]}


def save_interview(state: InterviewState):
    """save_interview node: freeze the transcript before leaving the subgraph."""
    analyst = as_analyst(state["analyst"])
    interview = format_transcript(state["messages"])

    return {
        "interview": interview,
        "interviews": [{"analyst": analyst.model_dump(), "transcript": interview}],
    }
