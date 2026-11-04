"""LLM API layer (Groq, openai/gpt-oss-120b) with retries."""
import time

from groq import APIConnectionError, Groq, RateLimitError

MODEL = "openai/gpt-oss-120b"


def get_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def chat(client, messages, temperature=0.3, max_tokens=2048, tools=None, json_mode=False, retries=3):
    kwargs = dict(model=MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if tools:
        kwargs.update(tools=tools, tool_choice="auto")
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for attempt in range(retries):
        try:
            return client.chat.completions.create(**kwargs)
        except (RateLimitError, APIConnectionError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
