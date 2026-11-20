import unittest

import pandas as pd

from src.attractions import DATA_PATH, load_attractions
from src.recommend import recommend_attractions
from src.weather import classify_monthly_weather, get_monthly_suitability


class RecommendationTests(unittest.TestCase):
    def test_current_and_both_distance(self):
        result = recommend_attractions(user_lat=38.25, user_lon=128.56, location_mode="current", top_n=1000)
        self.assertTrue(result["거리_km"].is_monotonic_increasing)
        self.assertTrue(result["테마유사도"].isna().all())
        result = recommend_attractions("T039", user_lat=38.25, user_lon=128.56,
                                      location_mode="both", max_distance_km=30, top_n=1000)
        self.assertNotIn("T039", set(result["관광지ID"]))
        self.assertTrue((result[["현재위치거리_km", "일정위치거리_km"]] <= 30).all().all())
        expected = (result["현재위치거리_km"] + result["일정위치거리_km"]) / 2
        pd.testing.assert_series_equal(result["거리_km"], expected, check_names=False)

    def test_weather_priority_and_optional_fallback(self):
        candidates = recommend_attractions("T039", top_n=1000)
        best, worst = candidates.iloc[0]["관광지ID"], candidates.iloc[-1]["관광지ID"]
        weather = {best: "보통", worst: "적합"}
        self.assertEqual(recommend_attractions("T039", weather=weather)["관광지ID"].tolist(), [worst])
        self.assertEqual(recommend_attractions("T039", weather=weather, include_normal=True)["관광지ID"].tolist(), [worst, best])
        self.assertEqual(recommend_attractions("T039", top_n=1, weather=weather, include_normal=True)["관광지ID"].tolist(), [worst])
        self.assertTrue(recommend_attractions("T039", weather={}).empty)
        self.assertTrue(recommend_attractions("T039", weather={best: "부적합", worst: "판단보류"}, include_normal=True).empty)

    def test_filters_and_empty_candidates(self):
        result = recommend_attractions("T039", indoor_preference="실내")
        self.assertTrue(result["실내구분"].eq("실내").all())
        self.assertTrue(recommend_attractions("T039", max_distance_km=0.000001).empty)
        self.assertTrue(recommend_attractions("T039", location_mode="both", user_lat=0, user_lon=0, max_distance_km=1).empty)

    def test_invalid_inputs(self):
        cases = [{"top_n": 0}, {"top_n": True}, {"max_distance_km": "30"},
                 {"max_distance_km": float("inf")}, {"location_mode": "bad"},
                 {"location_mode": "current", "user_lat": "38", "user_lon": 128},
                 {"location_mode": "current", "user_lat": 91, "user_lon": 128},
                 {"weather": {}, "month": "2025-02"}, {"weather": {"T001": "不明"}},
                 {"month": "1900-01"}, {"indoor_preference": "unknown"}]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError):
                recommend_attractions("T039", **options)
        with self.assertRaises(ValueError):
            recommend_attractions()
        with self.assertRaises(ValueError):
            recommend_attractions("unknown")

    def test_monthly_rules_match_knime(self):
        rows = pd.read_csv(DATA_PATH)
        actual = [classify_monthly_weather(i, t, r) for i, t, r in zip(
            rows["실내구분"], rows["평균기온(°C)"], rows["월합강수량(00~24h만)(mm)"])]
        self.assertEqual(actual, rows["날씨적합도"].tolist())
        for month in rows["일시"].unique():
            result = recommend_attractions("T039", top_n=1000, month=month)
            scores = get_monthly_suitability(month)
            self.assertEqual(set(result["관광지ID"]), set(scores[scores == "적합"].index) - {"T039"})

    def test_monthly_boundaries(self):
        for temp, rain, expected in [(10, 99, "적합"), (25, 99, "적합"), (20, 100, "보통"),
                                     (20, 200, "부적합"), (0, 0, "보통"), (30, 0, "보통"),
                                     (-1, None, "부적합"), (31, 0, "부적합"), (20, None, "판단보류")]:
            self.assertEqual(classify_monthly_weather("실외", temp, rain), expected)

    def test_score_and_cached_data_unchanged(self):
        before = load_attractions().copy(deep=True)
        result = recommend_attractions("T039", top_n=1000)
        expected = .6 * result["테마유사도"] + .4 / (1 + result["거리_km"] / 10)
        pd.testing.assert_series_equal(result["추천점수"], expected, check_names=False)
        self.assertTrue(result["추천점수"].is_monotonic_decreasing)
        pd.testing.assert_frame_equal(before, load_attractions())


if __name__ == "__main__":
    unittest.main()
