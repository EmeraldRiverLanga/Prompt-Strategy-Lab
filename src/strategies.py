ANSWER_FORMAT = 'Give only the final answer on a single line, prefixed with "Answer:".'


def zero_shot(table_text, question):
    """Baseline: the data and the question, with no examples, role, or reasoning steps."""
    prompt = (
        "You are given the 2019 World Happiness dataset as CSV:\n\n"
        f"{table_text}\n\n"
        f"Question: {question}\n"
        f"{ANSWER_FORMAT}"
    )
    return {"system": None, "prompt": prompt}


def chain_of_thought(table_text, question):
    """Chain-of-Thought: ask the model to reason step by step, then give the answer."""
    prompt = (
        "You are given the 2019 World Happiness dataset as CSV:\n\n"
        f"{table_text}\n\n"
        f"Question: {question}\n"
        "Reason step by step, but keep it brief: do NOT rewrite or reprint the dataset. "
        'Then give the final answer on a new line, prefixed with "Answer:".'
    )
    return {"system": None, "prompt": prompt}


def role_prompting(table_text, question):
    """Role prompting: assign the model an expert persona via the system message."""
    system = (
        "You are a meticulous data analyst who reads tabular data carefully "
        "and double-checks every figure before answering."
    )
    prompt = (
        "You are given the 2019 World Happiness dataset as CSV:\n\n"
        f"{table_text}\n\n"
        f"Question: {question}\n"
        f"{ANSWER_FORMAT}"
    )
    return {"system": system, "prompt": prompt}


def code_writing(table_text, question):
    """Super-prompt: the model writes pandas code instead of computing in its head."""
    system = (
        "You are a Python data analyst. You answer questions about a pandas "
        "DataFrame by writing code, never by computing in your head."
    )
    prompt = (
        "A pandas DataFrame `df` holds the 2019 World Happiness data. Its columns are:\n"
        "Overall rank, Country or region, Score, GDP per capita, Social support, "
        "Healthy life expectancy, Freedom to make life choices, Generosity, "
        "Perceptions of corruption\n\n"
        f"Question: {question}\n"
        "Write a single line of Python that evaluates to the answer, using `df`. "
        "Output only the expression, no explanation and no markdown fences."
    )
    return {"system": system, "prompt": prompt}
