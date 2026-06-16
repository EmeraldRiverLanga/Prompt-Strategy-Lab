import re

TOLERANCE = 0.1


def extract_answer(reply):
    """Return the model's final answer: the first non-empty line after the last 'Answer:' marker.

    Taking only the first line stops a long reasoning/data dump that happens to
    contain the truth string from counting as a correct answer (the q7 false positive).
    """
    marker = "answer:"
    lower = reply.lower()
    if marker in lower:
        tail = reply[lower.rindex(marker) + len(marker):]
        for line in tail.splitlines():
            if line.strip():
                return line.strip()
        return tail.strip()
    return reply.strip()


def is_correct(reply, truth):
    """Return True only if the model stated a final answer that matches the truth."""
    if "answer:" not in reply.lower():
        return False  # no final answer stated — the model rambled and never concluded
    answer = extract_answer(reply)
    if isinstance(truth, str):
        return truth.lower() in answer.lower()
    numbers = re.findall(r"-?\d+\.?\d*", answer)
    return any(abs(float(n) - truth) <= TOLERANCE for n in numbers)
