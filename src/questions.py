from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class Question:
    id: str
    difficulty: str  # "easy", "medium", or "hard"
    text: str  # the question sent to the model
    answer_fn: Callable[[pd.DataFrame], object]  # computes the true answer


QUESTIONS = [
    Question(
        id="q1",
        difficulty="easy",
        text="Which country has the highest happiness score?",
        answer_fn=lambda df: df.loc[df["Score"].idxmax(), "Country or region"],
    ),
    Question(
        id="q2",
        difficulty="medium",
        text="Among the 10 countries with the highest score, which has the lowest GDP per capita?",
        answer_fn=lambda df: df.nlargest(10, "Score")
        .nsmallest(1, "GDP per capita")
        .iloc[0]["Country or region"],
    ),
    Question(
        id="q3",
        difficulty="hard",
        text="How many countries have a happiness score above 6.0?",
        answer_fn=lambda df: int((df["Score"] > 6.0).sum()),
    ),
    Question(
        id="q4",
        difficulty="easy",
        text="Which country has the lowest happiness score?",
        answer_fn=lambda df: df.loc[df["Score"].idxmin(), "Country or region"],
    ),
    Question(
        id="q5",
        difficulty="easy",
        text="What is the happiness score of the highest-ranked country?",
        answer_fn=lambda df: float(df.loc[df["Overall rank"].idxmin(), "Score"]),
    ),
    Question(
        id="q6",
        difficulty="medium",
        text="Which country has the highest GDP per capita?",
        answer_fn=lambda df: df.loc[df["GDP per capita"].idxmax(), "Country or region"],
    ),
    Question(
        id="q7",
        difficulty="medium",
        text="Among countries with a happiness score above 7.0, which has the lowest healthy life expectancy?",
        answer_fn=lambda df: df[df["Score"] > 7.0]
        .nsmallest(1, "Healthy life expectancy")
        .iloc[0]["Country or region"],
    ),
    Question(
        id="q8",
        difficulty="hard",
        text="What is the average happiness score across all countries, rounded to two decimals?",
        answer_fn=lambda df: round(float(df["Score"].mean()), 2),
    ),
    Question(
        id="q9",
        difficulty="hard",
        text="How many countries have a GDP per capita above the dataset's average GDP per capita?",
        answer_fn=lambda df: int(
            (df["GDP per capita"] > df["GDP per capita"].mean()).sum()
        ),
    ),
    Question(
        id="q10",
        difficulty="hard",
        text="What is the difference between the highest and lowest happiness score, rounded to three decimals?",
        answer_fn=lambda df: round(float(df["Score"].max() - df["Score"].min()), 3),
    ),
]


def answer_key(df):
    """Compute the true answer for every question."""
    return {q.id: q.answer_fn(df) for q in QUESTIONS}


if __name__ == "__main__":
    from src.dataset import load_data

    df = load_data()
    for q in QUESTIONS:
        print(f"[{q.difficulty:6}] {q.id}: {q.answer_fn(df)}")
