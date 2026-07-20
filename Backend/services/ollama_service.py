import ollama
from collections.abc import Generator, Sequence

from config import OLLAMA_MODEL


def stream_chat(messages: Sequence[dict[str, str]], model: str = OLLAMA_MODEL) -> Generator[str, None, None]:
    """
    Stream response from Ollama.
    """

    stream = ollama.chat(
        model=model,
        messages=messages,
        stream=True
    )

    for chunk in stream:
        content = chunk["message"].get("content", "")
        if content:
            yield content
