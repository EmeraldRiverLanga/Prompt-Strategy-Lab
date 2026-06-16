import os

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"  # small, non-reasoning: keeps prompting-strategy differences visible

# Approximate OpenRouter rates for the default model (USD per 1M tokens).
# Provider routing can change these, so any cost figure derived from them is an estimate.
PRICE_PER_M_INPUT = 0.02
PRICE_PER_M_OUTPUT = 0.03

_USAGE = []  # token usage of every successful call since the last reset


def reset_usage():
    """Clear recorded token usage (call before measuring a strategy)."""
    _USAGE.clear()


def get_usage():
    """Aggregate token usage and an estimated cost since the last reset."""
    prompt = sum(u.get("prompt_tokens", 0) for u in _USAGE)
    completion = sum(u.get("completion_tokens", 0) for u in _USAGE)
    cost = prompt / 1_000_000 * PRICE_PER_M_INPUT + completion / 1_000_000 * PRICE_PER_M_OUTPUT
    return {
        "calls": len(_USAGE),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "est_cost_usd": round(cost, 5),
    }


def ask(prompt, system=None, model=DEFAULT_MODEL, temperature=0.0, retries=5):
    """Send a chat request to OpenRouter and return the reply text.

    Retries on an empty response, which some providers occasionally return.
    """
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to your .env file.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages, "temperature": temperature}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    last_error = None
    for _ in range(retries):
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text}")

        data = response.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")

        content = data["choices"][0]["message"]["content"]
        if content:
            if "usage" in data:
                _USAGE.append(data["usage"])
            return content
        last_error = "empty content"

    print(f"[warn] OpenRouter returned no content after {retries} tries; continuing with an empty reply.")
    return ""