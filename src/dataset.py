from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "2019.csv"


def load_data():
    """Read the 2019 happiness table and return it as a DataFrame."""
    return pd.read_csv(DATA_PATH)


if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
    top = df.loc[df["Score"].idxmax()]
    print("Highest score:", top["Country or region"], top["Score"])
