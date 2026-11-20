"""KNIME 월별 규칙 초안 재현용. 일 단위 예보나 실시간 추천에 사용하지 않는다."""

from functools import lru_cache

import pandas as pd

from src.attractions import DATA_PATH


def classify_monthly_weather(indoor_type, monthly_avg_temp, monthly_rainfall):
    """Rule Engine (#39)의 순서와 경계값을 그대로 적용한다.

    기온 단위는 ℃, 강수량은 월 합계 mm이다. 최고기온 조건은 없다.
    기온 결측만으로 판단보류하지 않는 것 역시 기존 초안의 동작이다.
    """
    if indoor_type == "실내":
        return "적합"

    has_temp = pd.notna(monthly_avg_temp)
    has_rain = pd.notna(monthly_rainfall)
    if indoor_type == "실외":
        if has_rain and monthly_rainfall >= 200:
            return "부적합"
        if has_temp and (monthly_avg_temp < 0 or monthly_avg_temp > 30):
            return "부적합"
        if has_temp and has_rain and 10 <= monthly_avg_temp <= 25 and monthly_rainfall < 100:
            return "적합"

    if not has_rain:
        return "판단보류"
    return "보통"


@lru_cache(maxsize=1)
def _load_monthly_weather():
    return pd.read_csv(
        DATA_PATH,
        usecols=["관광지ID", "일시", "실내구분", "평균기온(°C)", "월합강수량(00~24h만)(mm)"],
        encoding="utf-8",
    )


def get_monthly_suitability(month):
    """지정한 월(YYYY-MM)의 관광지별 적합도를 Python 규칙으로 계산한다."""
    data = _load_monthly_weather()
    rows = data[data["일시"] == month]
    if rows.empty:
        raise ValueError(f"월별 기상 자료가 없습니다: {month} (YYYY-MM)")
    if rows["관광지ID"].duplicated().any():
        raise ValueError(f"관광지ID·월 중복 자료가 있습니다: {month}")

    return pd.Series(
        [classify_monthly_weather(indoor, temp, rain)
         for indoor, temp, rain in zip(
             rows["실내구분"], rows["평균기온(°C)"], rows["월합강수량(00~24h만)(mm)"]
         )],
        index=rows["관광지ID"],
        name="날씨적합도",
    )
