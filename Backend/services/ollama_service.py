import os
from collections.abc import Generator, Sequence

from google import genai
from google.genai import types

from config import GEMINI_MODEL
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def stream_chat(
    messages: Sequence[dict[str, str]],
    system_instruction: str | None = None,
    model: str = GEMINI_MODEL,
) -> Generator[str, None, None]:

    contents = []

    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(text=message["content"])
                ]
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction
    )
    print(f"Using Gemini model: {model}")
    response = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text