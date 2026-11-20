from functools import lru_cache
from pathlib import Path

import pandas as pd
from src.attractions import load_attractions

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "theme_similarity.csv"
)


@lru_cache(maxsize=1)
def load_theme_similarity():
    """테마 간 유사도 표(6x6)를 한 번만 읽어 재사용한다."""
    return pd.read_csv(DATA_PATH, index_col=0, encoding="utf-8")


def get_theme_similarity(theme_a, theme_b):
    df = load_theme_similarity()
    for theme in (theme_a, theme_b):
        if theme not in df.index:
            raise ValueError(
                f"알 수 없는 테마: {theme!r} (가능한 값: {list(df.index)})"
            )
    return float(df.loc[theme_a, theme_b])


def get_attraction_similarity(name_a, name_b):
    attractions = load_attractions()

    attraction_a = attractions[attractions["관광지명"] == name_a]
    attraction_b = attractions[attractions["관광지명"] == name_b]

    if attraction_a.empty:
        raise ValueError(f"관광지를 찾을 수 없습니다: {name_a}")

    if attraction_b.empty:
        raise ValueError(f"관광지를 찾을 수 없습니다: {name_b}")

    theme_a = attraction_a.iloc[0]["테마명"]
    theme_b = attraction_b.iloc[0]["테마명"]

    return get_theme_similarity(theme_a, theme_b)


if __name__ == "__main__":
    score = get_theme_similarity("자연/힐링", "캠핑/스포츠")
    print(f"테마 유사도: {score:.2f}")