"""위치·테마 기반 추천. 월별 초안과 테스트 날씨 판정은 선택해서 적용한다."""

import argparse
from math import isfinite
from numbers import Real

from src.attractions import load_attractions
from src.distance import calculate_distance
from src.similarity import get_theme_similarity
from src.weather import get_monthly_suitability


THEME_WEIGHT = 0.6
DISTANCE_WEIGHT = 0.4


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{label}은 유한한 숫자여야 합니다.")
    return float(value)


def _coordinates(lat, lon):
    lat, lon = _number(lat, "위도"), _number(lon, "경도")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("위도·경도 범위를 확인해 주세요.")
    return lat, lon


def recommend_attractions(
    attraction_id=None, top_n=5, *, user_lat=None, user_lon=None,
    location_mode="itinerary", max_distance_km=None,
    indoor_preference=None, weather=None, month=None, include_normal=False,
):
    """적합 후보를 우선 추천하고, 선택 시 부족한 자리를 보통 후보로 채운다.

    weather는 {관광지ID: 판정} 형태의 테스트 입력이며 실시간 예보가 아니다.
    month는 YYYY-MM 형식의 월별 초안 검증 옵션이다. 둘은 함께 쓸 수 없다.
    both의 평가 거리는 두 거리의 평균이며, 최대 거리는 양쪽에 각각 적용한다.
    """
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("추천 개수는 1 이상의 정수여야 합니다.")
    if not isinstance(include_normal, bool):
        raise ValueError("include_normal은 True 또는 False여야 합니다.")
    if location_mode not in ("current", "itinerary", "both"):
        raise ValueError("위치 기준은 current, itinerary, both 중 하나입니다.")
    if indoor_preference not in (None, "실내", "실외"):
        raise ValueError("실내외 조건은 실내, 실외 또는 None입니다.")
    if max_distance_km is not None:
        max_distance_km = _number(max_distance_km, "최대 거리")
        if max_distance_km <= 0:
            raise ValueError("최대 거리는 0보다 커야 합니다.")
    if month is not None and weather is not None:
        raise ValueError("month와 weather는 동시에 사용할 수 없습니다.")
    if weather is not None:
        allowed = ("적합", "보통", "부적합", "판단보류")
        if not isinstance(weather, dict) or any(v not in allowed for v in weather.values()):
            raise ValueError("weather는 관광지ID와 적합·보통·부적합·판단보류 판정을 담은 딕셔너리입니다.")
    if location_mode in ("current", "both"):
        user_lat, user_lon = _coordinates(user_lat, user_lon)

    attractions = load_attractions()
    source = None
    if attraction_id is not None:
        selected = attractions[attractions["관광지ID"] == attraction_id]
        if selected.empty:
            raise ValueError(f"관광지를 찾을 수 없습니다: {attraction_id}")
        source = selected.iloc[0]
    if location_mode in ("itinerary", "both") and source is None:
        raise ValueError("기존 일정의 관광지ID가 필요합니다.")

    candidates = attractions[attractions["관광지ID"] != attraction_id].copy()
    if indoor_preference is not None:
        candidates = candidates[candidates["실내구분"] == indoor_preference].copy()

    if month is not None or weather is not None:
        suitability = get_monthly_suitability(month) if month is not None else weather
        candidates["날씨적합도"] = candidates["관광지ID"].map(suitability).astype("string").fillna("판단보류")
        accepted = ["적합", "보통"] if include_normal else ["적합"]
        candidates = candidates[candidates["날씨적합도"].isin(accepted)].copy()
        candidates["날씨우선순위"] = candidates["날씨적합도"].map({"적합": 0, "보통": 1})
    else:
        candidates["날씨적합도"] = "날씨 미반영"
        candidates["날씨우선순위"] = 0

    # 좌표가 없거나 범위를 벗어난 후보는 제외한다.
    valid = candidates["위도(도)"].between(-90, 90) & candidates["경도(도)"].between(-180, 180)
    candidates = candidates[valid].copy()
    distance_columns = []
    origins = []
    if location_mode in ("current", "both"):
        origins.append(("현재위치거리_km", user_lat, user_lon))
    if location_mode in ("itinerary", "both"):
        lat, lon = _coordinates(source["위도(도)"], source["경도(도)"])
        origins.append(("일정위치거리_km", lat, lon))
    for column, lat, lon in origins:
        candidates[column] = [
            calculate_distance(lat, lon, other_lat, other_lon)
            for other_lat, other_lon in zip(candidates["위도(도)"], candidates["경도(도)"])
        ]
        distance_columns.append(column)
    if max_distance_km is not None:
        candidates = candidates[candidates[distance_columns].le(max_distance_km).all(axis=1)].copy()
    candidates["거리_km"] = candidates[distance_columns].mean(axis=1)
    candidates["거리점수"] = 1 / (1 + candidates["거리_km"] / 10)

    if source is not None:
        theme_scores = {
            theme: get_theme_similarity(source["테마명"], theme)
            for theme in candidates["테마명"].unique()
        }
        candidates["테마유사도"] = candidates["테마명"].map(theme_scores)
        candidates["추천점수"] = THEME_WEIGHT * candidates["테마유사도"] + DISTANCE_WEIGHT * candidates["거리점수"]
    else:
        candidates["테마유사도"] = float("nan")
        candidates["추천점수"] = candidates["거리점수"]
    columns = ["관광지ID", "관광지명", "테마명", "실내구분", "날씨적합도",
               *distance_columns, "거리_km", "테마유사도", "추천점수"]
    return (candidates.sort_values(
        ["날씨우선순위", "추천점수", "거리_km", "관광지ID"], ascending=[True, False, True, True]
    ).head(top_n)[columns].reset_index(drop=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="위치·테마 기반 관광지 추천")
    parser.add_argument("attraction_id", nargs="?", help="기존 관광지ID (예: T039)")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--location-mode", choices=["current", "itinerary", "both"], default="itinerary")
    parser.add_argument("--user-lat", type=float)
    parser.add_argument("--user-lon", type=float)
    parser.add_argument("--max-distance-km", type=float)
    parser.add_argument("--indoor-preference", choices=["실내", "실외"])
    parser.add_argument("--month", help="월별 초안 검증용 YYYY-MM")
    parser.add_argument("--include-normal", action="store_true", help="적합 후보가 부족하면 보통 후보로 보충")
    args = parser.parse_args()
    try:
        result = recommend_attractions(**vars(args))
    except ValueError as error:
        parser.error(str(error))
    print(f"월별 초안 검증: {args.month} — 실시간 예보 아님" if args.month else "날씨 미반영")
    if result.empty:
        print("추천 조건에 맞는 관광지가 없습니다. 거리·실내외·날씨 조건을 확인해 주세요.")
    else:
        print(result.to_string(index=False, na_rep="—", float_format=lambda value: f"{value:.2f}"))
