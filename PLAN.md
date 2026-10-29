# Implementation Plan — AI Research Agent (LangGraph)

Target: reproduce the reference graph (`create_analysts → human_feedback → conduct_interview ×N →
write_section → [write_report | write_introduction | write_conclusion] → finalize_report`).

---

## 0. Status snapshot

### Progress log

| Phase | Status | Notes |
|---|---|---|
| 0 — Cleanup | ✅ done | persona bug, duplicate prompt, `.langgraph_api` untracked |
| 1 — State contract | ✅ done | `InterviewState` / `ResearchGraphState` split, reducers verified by test |
| 2 — Schemas & tools | ✅ done | `SearchQuery`, `Queries`, 2 Tavily tools, `run_search`/`format_docs` |
| 3 — Interview subgraph | ✅ done | `src/interview.py`, all 5 nodes, routing, 8 offline tests green |
| 4 — Fan-out | ⬜ next | `Send` per analyst |
| 5–8 | ⬜ todo | see §6 |

Deviations from the plan worth knowing:

- Added `utils/messages.py` (`message_text`, `format_transcript`): Gemini returns `content`
  as a **list of blocks**, so `"..." in message.content` fails. Everything now goes through helpers.
- `save_interview` labels lines `Analyst:` / `Expert:` (via `AIMessage.name == "expert"`) instead of
  `get_buffer_string`, which rendered every line as `AI:`.
- `route_messages` counts expert answers by `name`, not `HumanMessage`s (there is only one human
  message in the whole interview, so counting humans never terminates).
- `langgraph.json` now also registers the `interview` subgraph so you can test it in Studio.
- Real Gemini calls are **unusable from this network right now** (no response in 150 s), so all
  verification was done offline with a fake LLM + real Tavily (12 docs retrieved successfully).

### Baseline checks

Verified today by importing/running the code:

| Check | Result |
|---|---|
| `import utils.states` | ❌ `NameError: name 'MessageState' is not defined` |
| `import creating_analysts` | ❌ same error (state module is imported everywhere) |
| Analyst graph (phase 1) | ✅ correct topology once `states.py` is fixed |
| Gemini call | ✅ works, but **very slow from this network** (one call took 234 s) |
| Tavily call | ✅ works, 2.7 s, returns `{"results": [{url,title,content}]}` |
| `langchain-google-genai` / `langchain-tavily` | ✅ installed and declared |
| Tests | ❌ none |

So: **nothing runs right now** because `Interview` in `states.py` is not importable.

---

## 1. Target graph → node map

```
START
  └─ create_analysts ──► human_feedback ──(feedback)──► create_analysts
                              │
                              └─(approved)──► conduct_interview  (Send × N analysts)
                                                    │  ┌ inner subgraph ─────────────┐
                                                    │  │ START → ask_question        │
                                                    │  │   ask_question → search_web │
                                                    │  │              → search_web2  │
                                                    │  │   search_web*  → answer_question
                                                    │  │   answer_question ─(loop)→ ask_question
                                                    │  │   answer_question ─(done)→ save_interview → END
                                                    │  └────────────────────────────┘
                                                    ▼
                                              write_section
                                     ┌──────────────┼──────────────┐
                          write_report   write_introduction   write_conclusion
                                     └──────────────┼──────────────┘
                                                    ▼
                                            finalize_report → END
```

---

## 2. Gap matrix (current code vs target)

| Piece | Where | Status | Missing / broken |
|---|---|---|---|
| `create_analysts` | `utils/nodes.py` | ✅ done | — |
| `human_feedback` | `utils/nodes.py` | ✅ done | keep; it already normalises "okay/continue" |
| `should_continue` | `utils/edges.py` | ⚠️ partial | must route to `conduct_interview`, not `END` |
| `initiate_all_interviews` (Send fan-out) | `utils/edges.py` | ❌ missing | — |
| `InterviewState` | `utils/states.py` | ❌ broken | `MessageState` typo; conflated with outer state |
| `ResearchGraphState` | `utils/states.py` | ❌ missing | needed for outer graph |
| `generate_question` (`ask_question`) | `utils/nodes.py` | 🚧 unfinished | no `return`, no `AIMessage` wrapping |
| `search_web` / `search_web2` | — | ❌ missing | Tavily + query rewriting (`SearchQuery`) |
| `answer_question` | — | ❌ missing | context formatting + citation prompt |
| `route_messages` | `utils/edges.py` | ❌ missing | turn limit + "Thank you so much for your help!" |
| `save_interview` | — | ❌ missing | transcript formatting |
| interview subgraph builder | `src/answering_question.py` (empty) | ❌ missing | name it `src/interview.py` |
| `write_section` | — | ❌ missing | per-interview markdown section |
| `write_report` / `write_introduction` / `write_conclusion` | — | ❌ missing | three parallel nodes |
| `finalize_report` | — | ❌ missing | intro + body + conclusion |
| `SearchQuery` / `Queries` schema | `utils/objects.py` | ❌ missing | structured query rewriting |
| Tavily tools | `utils/tools.py` | ❌ placeholder (`"tools.py"`) | two search tools |
| Prompts | `utils/prompts.py` | ✅ present | duplicate `intro_conclusion_instructions`; Gemini braces risk |
| Final graph module | — | ❌ missing | `src/research_graph.py` |
| Registry | `langgraph.json` | ⚠️ | only registers phase-1 graph |
| Packaging | `src/utils/` | ⚠️ | no `__init__.py` (namespace pkg); `research_agent:main` script target doesn't exist |
| Repo hygiene | root | ⚠️ | `.langgraph_api/*.pckl` and `dist/` tracked in git |

---

## 3. Immediate blocking bugs (fix before anything else)

1. `utils/states.py:15` — `class Interview(MessageState)` → `MessagesState` (import from `langgraph.graph`).
2. `utils/states.py` — one class mixes inner (`messages`, `context`, `analyst`, `interview`) and outer
   (`sections`) fields. **Split into two states.**
3. `utils/nodes.py:51-60` — `generate_question` has no `return`, and the LLM answer must be returned as
   `{"messages": [answer]}` (an `AIMessage`) so the `add_messages` reducer appends it.
4. `utils/objects.py:12` — `persona` prints `self.affiliation` twice; should be `self.description`.
5. `utils/tools.py` — constructing `TavilySearch` before `load_dotenv()` raises
   `ValidationError: Did not find tavily_api_key`. `load_dotenv()` must run at module import top.
6. `utils/prompts.py` — `intro_conclusion_instructions` is defined twice (lines 129 and 151);
   delete one. Prompts must not contain stray `{}` or `.format()` will raise `KeyError`.
7. `.gitignore` — add `.langgraph_api/`, `dist/`, and untrack the checkpoint `.pckl` files.

---

## 4. Architecture decisions (the parts that usually break)

### 4.1 Two state classes, strict separation

```python
# utils/states.py
class InterviewState(MessagesState):          # inner subgraph only
    max_num_turns: int
    context: Annotated[list, operator.add]
    analyst: Analyst
    interview: str
    interviews: Annotated[list, operator.add]  # written by save_interview for the parent

class ResearchGraphState(TypedDict):           # outer graph only
    topic: str
    max_analysts: int
    human_analyst_feedback: NotRequired[Optional[str]]
    analysts: NotRequired[List[Analyst]]
    interviews: Annotated[list, operator.add]  # fan-in from the N subgraph runs
    sections: Annotated[list, operator.add]    # fan-in from the 3 writers if you Send them
    introduction: str
    content: str
    conclusion: str
    final_report: str
```

Why `interviews` **and** `sections`: the raw transcripts must survive until `write_section` runs, and
written sections must not overwrite them. Using one key with `operator.add` duplicates data on the
second pass.

### 4.2 Fan-out via `Send`, fan-in via reducer

```python
def initiate_all_interviews(state: ResearchGraphState):
    if state.get("human_analyst_feedback"):
        return "create_analysts"                      # revise path
    return [                                          # fan-out path
        Send("conduct_interview", {
            "analyst": a,
            "max_num_turns": 2,
            "context": [],
            "interview": "",
            "messages": [HumanMessage(content=f"So you said you were writing an article on {state['topic']}?")],
        })
        for a in state["analysts"]
    ]
```

**One** conditional edge from `human_feedback` returning either a node name or `list[Send]`.
Do **not** attach two conditional edges (one for routing, one for fan-out) — both fire and the
interviews run twice. Do not add `END` here; the graph ends at `finalize_report`.

`interviews` must have `operator.add` in **both** states, otherwise N parallel subgraph writes to the
same key raise `InvalidUpdateError`.

### 4.3 Interview subgraph

```python
# edges.py
def route_messages(state: InterviewState) -> Literal["ask_question", "save_interview"]:
    msgs = state["messages"]
    turns = sum(isinstance(m, HumanMessage) for m in msgs)
    if turns > state["max_num_turns"]:
        return "save_interview"
    if "Thank you so much for your help" in msgs[-1].content:
        return "save_interview"
    return "ask_question"
```

Wiring (`src/interview.py`):

```python
b = StateGraph(InterviewState)
b.add_node("ask_question", generate_question)
b.add_node("search_web", search_web)
b.add_node("search_web2", search_web2)
b.add_node("answer_question", answer_question)
b.add_node("save_interview", save_interview)

b.add_edge(START, "ask_question")
b.add_edge("ask_question", "search_web")
b.add_edge("ask_question", "search_web2")
b.add_edge("search_web", "answer_question")
b.add_edge("search_web2", "answer_question")
b.add_conditional_edges("answer_question", route_messages, ["ask_question", "save_interview"])
b.add_edge("save_interview", END)
interview_graph = b.compile()
```

Nodes:
- `search_web(state)` → `llm.with_structured_output(SearchQuery)` on `state["messages"]` → 1 query →
  `tavily_search.invoke({"query": q})` → `{"context": [docs]}`.
- `search_web2(state)` → same but multi-query (`Queries`, 2-3 queries, dedupe by URL) and
  `max_results=5`. Two *different* tools is what the reference graph shows; keep them independent so
  you can measure which one retrieves better.
- `answer_question(state)` → build `<Document source="url">content</Document>` blocks →
  `answer_instructions.format(goals=..., context=...)` + `state["messages"]` → return `{"messages": [answer]}`.
- `save_interview(state)` → join messages into `"Analyst: …\nExpert: …"` →
  `{"interview": text, "interviews": [{"analyst": analyst.model_dump(), "transcript": text}]}`.

### 4.4 Outer wiring

```python
builder.add_node("conduct_interview", interview_graph)      # compiled subgraph as a node
builder.add_node("write_section", write_section)
...
builder.add_edge("conduct_interview", "write_section")      # implicit fan-in: waits for all Sends
builder.add_edge("write_section", "write_report")
builder.add_edge("write_section", "write_introduction")
builder.add_edge("write_section", "write_conclusion")
builder.add_edge(["write_report", "write_introduction", "write_conclusion"], "finalize_report")
builder.add_edge("finalize_report", END)
```

`write_section` runs once, after all interviews complete, and loops over `state["interviews"]`
(keeps the picture you have). Optional later optimisation: `Send` one `write_section` per interview.

---

## 5. File plan

```
src/
├─ research_graph.py        # NEW  final graph (registered in langgraph.json)
├─ interview.py             # NEW  conduct_interview subgraph (replaces empty answering_question.py)
├─ creating_analysts.py     # keep as phase-1 graph for fast testing
└─ utils/
   ├─ states.py             # REWRITE  InterviewState + ResearchGraphState
   ├─ objects.py            # EDIT     persona fix + SearchQuery/Queries
   ├─ nodes.py              # EDIT     finish generate_question (analyst nodes)
   ├─ interview_nodes.py    # NEW      search_web, search_web2, answer_question, save_interview
   ├─ report_nodes.py       # NEW      write_section, write_report, write_introduction,
   │                        #          write_conclusion, finalize_report
   ├─ edges.py              # EDIT     route_messages, initiate_all_interviews
   ├─ tools.py              # REWRITE  Tavily tools (after load_dotenv)
   ├─ prompts.py            # EDIT     de-dupe intro_conclusion_instructions
   └─ __init__.py           # NEW      make it a real package
```

`langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "research_graph": "./src/research_graph.py:graph",
    "create_analysts": "./src/creating_analysts.py:graph"
  },
  "env": ".env"
}
```

---

## 6. Execution phases (each ends in something runnable)

| # | Phase | Deliverable | Definition of done | Est. |
|---|---|---|---|---|
| 0 | Cleanup | fix `states.py` typo, persona bug, de-dupe prompt, `.gitignore` | `import creating_analysts` passes | 30 min |
| 1 | State contract | `InterviewState` + `ResearchGraphState` + reducers | both import; `graph.get_graph()` renders phase 1 | 45 min |
| 2 | Schemas & tools | `SearchQuery`, `Queries`, `tools.py` with 2 Tavily tools | real search returns docs through the tool | 45 min |
| 3 | Interview subgraph | `generate_question`, `search_web(2)`, `answer_question`, `route_messages`, `save_interview`, `src/interview.py` | 1-analyst interview produces a transcript with ≥2 turns and exits on the thank-you | 3 h |
| 4 | Fan-out | `initiate_all_interviews` + subgraph as node | 3 analysts → 3 interviews in state | 1 h |
| 5 | Sections | `write_section` | `len(sections) == len(analysts)`, each has `##` + `### Sources` | 1 h |
| 6 | Report | 3 writers + `finalize_report` + full wiring | `final_report` non-empty, contains intro, insights, conclusion | 1.5 h |
| 7 | Registry & docs | `langgraph.json`, README with run instructions | `langgraph dev` exposes `research_graph` | 30 min |
| 8 | Tests & hardening | stub-LLM harness, timeouts/retries, cost guards | CI-less smoke test passes without network | 2 h |

Total ≈ 10–11 h of work; phases 0–2 are prerequisites for everything else.

---

## 7. Test strategy (no API cost)

Build a `tests/test_graph_smoke.py` with a fake LLM (the same pattern already used to validate phase 1):

- `FakeLLM.with_structured_output(Perspectives)` → 2 analysts.
- `FakeLLM.with_structured_output(SearchQuery)` → fixed query.
- Monkeypatch `utils.tools.tavily_search.invoke` → canned `{"results": […]}`.
- Compile with `InMemorySaver()` and assert:
  1. first `invoke` interrupts at `human_feedback`;
  2. `Command(resume="okay")` reaches `finalize_report` and sets `final_report`;
  3. `Command(resume="focus on X")` regenerates analysts (loop back);
  4. `len(interviews) == len(analysts)` and `len(sections) == len(analysts)`;
  5. interview loop terminates at `max_num_turns` even if the LLM never says thank you.

Use `LANGGRAPH_STRICT_MSGPACK` awareness: `Analyst` must be importable at its module path for
checkpoint deserialisation (already the case).

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Gemini latency (234 s observed) stalls the interview loop | `ChatGoogleGenerativeAI(timeout=60, max_retries=2)`, `max_num_turns=2`, `max_results=2`, trace off (`LANGSMITH_TRACING_V2=false` — key currently 403s) |
| Consecutive same-role messages (AI question → AI question loop) rejected | Test early in phase 3; if it errors, insert a `HumanMessage("continue")` shim or merge turns |
| `recursion_limit` exceeded (each interview turn ≈ 4 steps, ×N analysts) | set `recursion_limit≈60` in the run config; keep `max_num_turns` ≤ 3 |
| Parallel writes to the same non-reducer key → `InvalidUpdateError` | `interviews`/`context`/`sections` all use `operator.add` |
| State bloat (full search context kept forever) | keep 1–2 docs per query, do not copy `context` into `sections` |
| Structured output fails on Gemini | `with_structured_output(..., method="json_schema")` fallback; validate with `model_validate` |
| `interrupt` without checkpointer raises | `langgraph dev` supplies one; scripts must `compile(checkpointer=InMemorySaver())` |
| `.env` key naming | Gemini only auto-reads `GOOGLE_API_KEY`/`GEMINI_API_KEY` — keep the explicit `api_key=` in `models.py` |

---

## 9. Suggested commit sequence

1. `fix: split interview/research state, persona + prompt cleanup`
2. `feat: tavily tools + search schemas`
3. `feat: interview subgraph (ask → search → answer → save)`
4. `feat: Send fan-out per analyst`
5. `feat: section + report writers, finalize_report`
6. `chore: registry, package init, gitignore, smoke tests`
