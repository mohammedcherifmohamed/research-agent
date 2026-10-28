import os

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
    temperature=0,
)
