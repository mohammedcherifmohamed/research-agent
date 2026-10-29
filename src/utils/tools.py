import os

from dotenv import load_dotenv
from langchain_tavily import TavilySearch

# Must run before TavilySearch() is created: it reads TAVILY_API_KEY from the env.
load_dotenv()

_API_KEY = os.getenv("TAVILY_API_KEY")

# Two independent search tools: cheap/broad and deep/narrow.
tavily_search = TavilySearch(
    max_results=2,
    topic="general",
    search_depth="basic",
    tavily_api_key=_API_KEY,
)

tavily_search_2 = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced",
    tavily_api_key=_API_KEY,
)


def run_search(tool: TavilySearch, query: str) -> list[dict]:
    """Run one search and normalise the result into a list of docs.

    Never raises: a failing search becomes a document explaining the failure,
    so one bad tool call cannot kill an interview.
    """
    try:
        raw = tool.invoke({"query": query})
    except Exception as exc:  # noqa: BLE001 - search failure must not break the graph
        return [
            {
                "url": "",
                "title": f"Search failed: {query}",
                "content": f"The web search failed ({type(exc).__name__}: {exc}).",
            }
        ]

    results = raw.get("results", []) if isinstance(raw, dict) else raw or []

    docs: list[dict] = []
    for item in results:
        if isinstance(item, dict):
            docs.append(
                {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                }
            )
        else:
            docs.append({"url": "", "title": "", "content": str(item)})
    return docs


def format_docs(docs: list[dict]) -> str:
    """Format retrieved docs the way ``answer_instructions`` expects them."""
    if not docs:
        return "No search results were retrieved."

    blocks = []
    for doc in docs:
        source = doc.get("url") or "unknown"
        title = doc.get("title") or ""
        content = doc.get("content") or ""
        blocks.append(
            f'<Document source="{source}" title="{title}">\n{content}\n</Document>'
        )
    return "\n\n".join(blocks)
