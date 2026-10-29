"""Small helpers for reading and formatting chat messages.

Gemini (and other providers) may return ``content`` as a list of content blocks
instead of a plain string, so never compare ``message.content`` directly.
"""

from typing import Any

from langchain.messages import AIMessage, HumanMessage


def message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(part for part in parts if part)
    return str(content)


def format_transcript(messages: list) -> str:
    """Render an interview as ``Analyst: ...`` / ``Expert: ...`` lines."""
    lines: list[str] = []
    for message in messages:
        text = message_text(message).strip()
        if not text:
            continue
        is_expert = isinstance(message, AIMessage) and message.name == "expert"
        role = "Expert" if is_expert else "Analyst"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)
