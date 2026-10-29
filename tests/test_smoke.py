"""Offline smoke tests: no Gemini / Tavily calls are made."""

import operator
from typing import Annotated, NotRequired, get_args, get_origin

import pytest
from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from utils.objects import Analyst, Perspectives, Queries, SearchQuery
from utils.prompts import (
    analyst_instructions,
    answer_instructions,
    intro_conclusion_instructions,
    question_instructions,
    report_writer_instructions,
    section_writer_instructions,
)
from utils.states import InterviewState, ResearchGraphState

ANALYST = Analyst(
    affiliation="Acme Labs",
    name="Ada",
    role="AI researcher",
    description="focuses on agentic systems",
)


class FakeStructured:
    def __init__(self, schema, max_analysts: int = 2):
        self.schema = schema
        self.max_analysts = max_analysts

    def invoke(self, messages):
        if self.schema is Perspectives:
            return Perspectives(
                analysts=[
                    Analyst(
                        affiliation=f"Org {i}",
                        name=f"Analyst {i}",
                        role=f"Role {i}",
                        description=f"description {i}",
                    )
                    for i in range(1, self.max_analysts + 1)
                ]
            )
        if self.schema is Queries:
            return Queries(queries=["query one", "query two", "query two"])
        if self.schema is SearchQuery:
            return SearchQuery(search_query="single query")
        raise AssertionError(f"unexpected schema {self.schema}")


class FakeLLM:
    def __init__(self, thanks_on_question: int | None = None):
        self.thanks_on_question = thanks_on_question
        self.questions = 0
        self.answers = 0

    def with_structured_output(self, schema):
        return FakeStructured(schema)

    def invoke(self, messages):
        system = str(messages[0].content)
        if "You are an analyst tasked with interviewing" in system:
            self.questions += 1
            if self.thanks_on_question == self.questions:
                return AIMessage(content="Thank you so much for your help!")
            return AIMessage(content=f"Question {self.questions}?")
        if "You are an expert being interviewed" in system:
            self.answers += 1
            return AIMessage(content=f"Answer {self.answers} [1]")
        if "creating a set of AI analyst personas" in system:
            raise AssertionError("analyst creation must go through structured output")
        raise AssertionError(f"unexpected prompt: {system[:80]}")


@pytest.fixture
def fake_llm(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr("utils.nodes.llm", llm)
    monkeypatch.setattr("utils.interview_nodes.llm", llm)
    return llm


@pytest.fixture
def fake_search(monkeypatch):
    calls: list[str] = []

    def fake_run_search(tool, query):
        calls.append(query)
        return [
            {"url": f"https://example.com/{len(calls)}", "title": "Example", "content": "body"},
            {"url": "https://example.com/dup", "title": "Dup", "content": "body"},
        ]

    monkeypatch.setattr("utils.interview_nodes.run_search", fake_run_search)
    return calls


# --------------------------------------------------------------------------- #
# Phase 1: analysts + human feedback
# --------------------------------------------------------------------------- #


def _analyst_graph():
    from creating_analysts import builder

    return builder.compile(checkpointer=InMemorySaver())


def test_analyst_graph_interrupts_then_approves(fake_llm):
    graph = _analyst_graph()
    config = {"configurable": {"thread_id": "approve"}}

    state = graph.invoke({"topic": "agents", "max_analysts": 2}, config)
    assert "__interrupt__" in state
    assert len(state["analysts"]) == 2

    final = graph.invoke(Command(resume="okay"), config)
    assert graph.get_state(config).next == ()
    assert len(final["analysts"]) == 2


def test_analyst_graph_feedback_regenerates(fake_llm):
    graph = _analyst_graph()
    config = {"configurable": {"thread_id": "revise"}}

    graph.invoke({"topic": "agents", "max_analysts": 2}, config)
    state = graph.invoke(Command(resume="focus on security"), config)

    assert state["human_analyst_feedback"] == "focus on security"
    assert graph.get_state(config).next == ("human_feedback",)


# --------------------------------------------------------------------------- #
# Phase 3: interview subgraph
# --------------------------------------------------------------------------- #


def _run_interview(max_num_turns: int, thanks_on_question: int | None):
    from interview import interview_graph

    config = {"configurable": {"thread_id": f"itw-{max_num_turns}-{thanks_on_question}"}}
    return interview_graph.invoke(
        {
            "analyst": ANALYST,
            "max_num_turns": max_num_turns,
            "context": [],
            "interview": "",
            "messages": [HumanMessage(content="So you said you were writing an article on agents?")],
        },
        config,
    )


def test_interview_ends_on_thank_you(fake_llm, fake_search):
    fake_llm.thanks_on_question = 2

    state = _run_interview(max_num_turns=5, thanks_on_question=2)

    assert fake_llm.answers == 2
    assert "Expert: Answer 2" in state["interview"]
    assert state["interview"].startswith("Analyst:")
    assert len(state["interviews"]) == 1
    assert state["interviews"][0]["analyst"]["name"] == "Ada"
    # both search nodes ran for each of the 2 turns
    assert len(fake_search) >= 4


def test_interview_ends_on_turn_limit(fake_llm, fake_search):
    fake_llm.thanks_on_question = None

    state = _run_interview(max_num_turns=1, thanks_on_question=None)

    assert fake_llm.answers == 1
    assert "Expert: Answer 1" in state["interview"]


def test_search_web2_deduplicates(fake_llm, fake_search):
    from utils.interview_nodes import search_web2

    state = {
        "analyst": ANALYST,
        "messages": [HumanMessage(content="question?")],
        "context": [],
    }
    update = search_web2(state)

    urls = [doc["url"] for doc in update["context"]]
    assert len(urls) == len(set(urls))
    assert "https://example.com/dup" in urls
    # 3 queries were asked, duplicates removed
    assert len(fake_search) == 3
    assert len(urls) == 4


# --------------------------------------------------------------------------- #
# Contracts that keep the parallel fan-out safe
# --------------------------------------------------------------------------- #


def _reducer(annotation):
    """Return the reducer metadata of a (possibly NotRequired-wrapped) Annotated type."""
    if get_origin(annotation) is NotRequired:
        annotation = get_args(annotation)[0]
    assert get_origin(annotation) is Annotated, annotation
    return get_args(annotation)[1:]


def test_parallel_keys_have_reducers():
    for key in ("context", "interviews"):
        assert _reducer(InterviewState.__annotations__[key]) == (operator.add,)
    for key in ("interviews", "sections"):
        assert _reducer(ResearchGraphState.__annotations__[key]) == (operator.add,)


def test_prompts_format():
    assert "agents" in analyst_instructions.format(
        topic="agents", human_analyst_feedback="none", max_analysts=2
    )
    assert "my-goals" in question_instructions.format(goals="my-goals")
    assert "ctx" in answer_instructions.format(goals="goals", context="ctx")
    assert "focus" in section_writer_instructions.format(focus="focus")
    assert "topic" in report_writer_instructions.format(topic="topic", context="ctx")
    assert "intro" in intro_conclusion_instructions.format(
        topic="topic", formatted_str_sections="intro"
    )


def test_persona_uses_description():
    persona = ANALYST.persona
    assert ANALYST.description in persona
    assert persona.count("Acme Labs") == 1
