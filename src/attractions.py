
from functools import lru_cache
from pathlib import Path

import pandas as pd


DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "weather_suitability_monthly_draft.csv"
)

ATTRACTION_COLUMNS = [
    "관광지ID",
    "관광지명",
    "테마명",
    "실내구분",
    "위도(도)",
    "경도(도)",
]


@lru_cache(maxsize=1)
def load_attractions():
    df = pd.read_csv(
        DATA_PATH,
        usecols=ATTRACTION_COLUMNS,
        encoding="utf-8",
    )

    attractions = df.drop_duplicates(subset=["관광지ID"])

    return attractions.reset_index(drop=True)


if __name__ == "__main__":
    attractions = load_attractions()

    print(f"관광지 수: {len(attractions)}")
    print(attractions.head(5).to_string(index=False))
