"""Quick check that the environment is ready: key loads and a live call works."""

from src.llm_client import ask

if __name__ == "__main__":
    print("Sending a test prompt to OpenRouter...")
    reply = ask("Reply with exactly the word: OK")
    print("Model replied:", reply)
    print(
        "Setup works."
        if "OK" in reply.upper()
        else "Unexpected reply — check the model name."
    )
