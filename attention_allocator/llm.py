import os
from typing import List, Dict, Any

import openai  # pip install openai


def llm_call(system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
    """
    Thin wrapper around OpenAI Chat Completions.
    Set OPENAI_API_KEY in your environment before calling this.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    resp = openai.ChatCompletion.create(model=model, messages=messages)
    return resp["choices"][0]["message"]["content"].strip()
