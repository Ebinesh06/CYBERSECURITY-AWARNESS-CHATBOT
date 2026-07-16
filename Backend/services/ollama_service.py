import ollama


def stream_chat(messages, model="llama3"):
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