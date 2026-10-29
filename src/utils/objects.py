from pydantic import BaseModel, Field
from typing import List


class Analyst(BaseModel):
    affiliation: str = Field(description="primary affiliation of the analyst.")
    name: str = Field(description="name of the analyst")
    role: str = Field(description="Role of the analyst in the context of the topic")
    description: str = Field(
        description="description of the analyst focus, concerns and motives"
    )

    @property
    def persona(self) -> str:
        return (
            f"name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Affiliation: {self.affiliation}\n"
            f"Description: {self.description}"
        )


class Perspectives(BaseModel):
    analysts: List[Analyst] = Field(
        description="comprehensive list of analysts with their roles and affiliation"
    )


class SearchQuery(BaseModel):
    search_query: str = Field(description="Query for web search.")


class Queries(BaseModel):
    queries: List[str] = Field(
        description="2 to 3 distinct web search queries covering different angles of the question"
    )


def as_analyst(value: Analyst | dict) -> Analyst:
    """Checkpoints may give us the analyst back as a plain dict."""
    return value if isinstance(value, Analyst) else Analyst.model_validate(value)
