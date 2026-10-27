from pydantic import BaseModel , Field
from typing import List

class Analyst(BaseModel) : 
    affiliation: str = Field(description="primary affiliation of the analyst.")
    name : str =  Field(description="name of the analyst")
    role:str = Field(description="Role of the analyst in the context of the topic")
    description:str = Field(description="description of the analyst focus , concerns and motives")

    @property
    def persona(self) -> str:
        return f"name: {self.name}\nRole: {self.role}\nAffiliation: {self.affiliation}\nDescription: {self.affiliation}"


class Perspectives(BaseModel):
    analysts:List[Analyst] = Field(description="comprehensive list of analysts with theire roles and affiliation")
    