"""수업에서 배운 Streamlit으로 일정 입력과 관광지 추천을 연결한다."""
from datetime import date, time, datetime

import pandas as pd
import streamlit as st

from src.attractions import DATA_PATH, load_attractions
from src.recommend import THEME_WEIGHT, DISTANCE_WEIGHT, recommend_attractions


# 1. 화면과 관광지 목록 준비
st.set_page_config(page_title="NUBI", page_icon="🌤️")
st.title("🌤️ NUBI")
st.write("여행 일정을 입력하고 대체 관광지를 찾아보세요.")
st.caption("실시간 날씨와 실제 도로 이동시간은 아직 반영하지 않습니다.")
attractions = load_attractions()
name_counts = attractions["관광지명"].value_counts()
labels = {
    row["관광지ID"]: row["관광지명"] if name_counts[row["관광지명"]] == 1
    else f"{row['관광지명']} ({row['관광지ID']})"
    for _, row in attractions.iterrows()
}
ids_by_label = {label: place_id for place_id, label in labels.items()}
names = dict(zip(attractions["관광지ID"], attractions["관광지명"]))


# 2. 화면이 다시 실행돼도 일정과 마지막 결과 유지
for key, value in {
    "itinerary": [], "recommendation_result": None,
    "recommendation_conditions": None, "editor_version": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_result():
    st.session_state.recommendation_result = None
    st.session_state.recommendation_conditions = None


# 3. 일정 추가
st.header("1. 여행 일정")
with st.form("add_schedule"):
    visit_date = st.date_input("방문 날짜", value=date.today())
    visit_time = st.time_input("방문 시간", value=time(10, 0))
    selected_id = st.selectbox("방문할 관광지", list(labels), format_func=labels.get)
    add = st.form_submit_button("일정 추가")
if add:
    st.session_state.itinerary.append({
        "날짜": visit_date.isoformat(), "시간": visit_time.strftime("%H:%M"),
        "관광지ID": selected_id, "관광지명": names[selected_id],
    })
    st.session_state.editor_version += 1
    clear_result()
    st.success("일정을 추가했습니다.")


# 4. 일정 수정: 이름을 선택하면 ID도 함께 바꿔서 저장
if st.session_state.itinerary:
    rows = [{"날짜": date.fromisoformat(item["날짜"]), "시간": item["시간"],
             "관광지": labels[item["관광지ID"]]} for item in st.session_state.itinerary]
    with st.form("edit_schedule"):
        edited = st.data_editor(
            pd.DataFrame(rows), hide_index=True, num_rows="dynamic",
            key=f"schedule_editor_{st.session_state.editor_version}",
            column_config={
                "날짜": st.column_config.DateColumn("날짜", required=True),
                "시간": st.column_config.TextColumn("시간", help="예: 10:00 (24시간 형식)", required=True),
                "관광지": st.column_config.SelectboxColumn("관광지", options=list(ids_by_label), required=True),
            },
        )
        save = st.form_submit_button("일정 수정 저장")
    if save:
        try:
            updated = []
            for _, row in edited.iterrows():
                if row.isna().any():
                    raise ValueError("날짜, 시간, 관광지를 모두 입력해 주세요.")
                parsed_time = datetime.strptime(str(row["시간"]).strip(), "%H:%M")
                place_id = ids_by_label.get(row["관광지"])
                if place_id is None:
                    raise ValueError("목록에 있는 관광지를 선택해 주세요.")
                updated.append({
                    "날짜": pd.Timestamp(row["날짜"]).date().isoformat(),
                    "시간": parsed_time.strftime("%H:%M"),
                    "관광지ID": place_id, "관광지명": names[place_id],
                })
            st.session_state.itinerary = updated
            st.session_state.editor_version += 1
            clear_result()
            st.rerun()
        except (ValueError, TypeError):
            st.error("날짜와 관광지를 확인하고 시간을 10:00 같은 형식으로 입력해 주세요.")
    st.caption("표를 편집한 뒤 ‘일정 수정 저장’을 눌러 주세요. 일정은 현재 세션에만 저장됩니다.")
else:
    st.info("일정을 추가하거나 아래에서 기준 관광지를 직접 선택하세요.")


# 5. 추천 위치와 기준 관광지 선택
st.header("2. 대체 관광지 추천")
modes = {"기존 일정 위치": "itinerary", "현재 위치": "current", "두 위치 모두": "both"}
mode = modes[st.radio("추천 위치 기준", list(modes))]
use_theme = st.checkbox("기존 관광지와 비슷한 테마로 추천받기") if mode == "current" else True
attraction_id = None
schedule_context = None
if use_theme:
    use_schedule = bool(st.session_state.itinerary) and st.checkbox("저장한 일정에서 기준 관광지 선택", value=True)
    if use_schedule:
        itinerary = st.session_state.itinerary
        index = st.selectbox("변경할 일정", list(range(len(itinerary))),
                             format_func=lambda i: f"{i + 1}. {itinerary[i]['날짜']} {itinerary[i]['시간']} · {itinerary[i]['관광지명']}")
        item = itinerary[index]
        attraction_id = item["관광지ID"]
        schedule_context = (index, item["날짜"], item["시간"], attraction_id)
        st.caption("선택한 일정의 대체 후보를 찾습니다. 일정은 자동으로 변경하지 않습니다.")
    else:
        attraction_id = st.selectbox("기준 관광지", list(labels), format_func=labels.get)

user_lat = user_lon = None
if mode in ("current", "both"):
    st.caption("좌표를 직접 입력하세요. 기본값은 현재 위치가 아닌 봉포해변 테스트 좌표입니다.")
    left, right = st.columns(2)
    with left:
        user_lat = st.number_input("위도", min_value=-90.0, max_value=90.0, value=38.244892, format="%.6f")
    with right:
        user_lon = st.number_input("경도", min_value=-180.0, max_value=180.0, value=128.572088, format="%.6f")


# 6. 거리와 실내외 조건
max_distance = None
if st.checkbox("최대 거리 설정", value=True):
    max_distance = st.number_input("최대 거리(km)", min_value=1.0, value=30.0, step=5.0)
if mode == "both":
    st.caption("두 위치에서 각각 제한 거리 이내여야 하며, 점수에는 평균 거리를 사용합니다.")
indoor = st.selectbox("실내외 조건", ["전체", "실내", "실외"])
top_n = st.slider("추천 개수", 1, 10, 5)


# 7. 월별 자료는 실시간 예보와 구분해서 테스트
@st.cache_data
def load_available_months():
    data = pd.read_csv(DATA_PATH, usecols=["일시"], encoding="utf-8")
    return sorted(data["일시"].dropna().unique().tolist())


month = None
include_normal = False
with st.expander("월별 날씨 초안 테스트"):
    use_month = st.checkbox("저장된 월별 자료로 날씨 필터 시험하기")
    st.caption("여행 날짜의 예보가 아닙니다. 과거 월별 자료로 추천 규칙만 확인합니다.")
    if use_month:
        month = st.selectbox("테스트할 월", load_available_months())
        include_normal = st.checkbox("적합한 후보가 부족하면 보통 후보로 보충")


# 8. 버튼을 누를 때 추천 실행
conditions = dict(attraction_id=attraction_id, top_n=top_n, user_lat=user_lat,
                  user_lon=user_lon, location_mode=mode, max_distance_km=max_distance,
                  indoor_preference=None if indoor == "전체" else indoor,
                  month=month, include_normal=include_normal)
context = {"conditions": conditions.copy(), "schedule": schedule_context}
if st.button("추천받기", type="primary"):
    try:
        with st.spinner("추천 관광지를 찾고 있어요..."):
            result = recommend_attractions(**conditions)
        st.session_state.recommendation_result = result
        st.session_state.recommendation_conditions = context
    except ValueError as error:
        st.error(str(error))
        clear_result()


# 9. 사용자에게 필요한 항목만 표시
result = st.session_state.recommendation_result
saved = st.session_state.recommendation_conditions
if result is not None:
    st.header("3. 추천 결과")
    if context != saved:
        st.info("입력 조건이 바뀌었습니다. ‘추천받기’를 다시 눌러 주세요.")
    previous = saved["conditions"]
    st.caption(f"{previous['month']} 월별 초안 기준 — 실제 여행 날짜의 예보가 아닙니다."
               if previous["month"] else "이 결과는 날씨를 반영하지 않았습니다.")
    if result.empty:
        st.warning("조건에 맞는 관광지가 없습니다. 거리나 실내외 조건을 조정해 보세요.")
    else:
        columns = {"관광지명": "관광지", "테마명": "테마", "실내구분": "실내외", "날씨적합도": "날씨 판정"}
        if previous["location_mode"] == "both":
            columns.update({"현재위치거리_km": "현재 위치에서(km)",
                            "일정위치거리_km": "기존 관광지에서(km)", "거리_km": "평균 거리(km)"})
        else:
            columns["거리_km"] = "거리(km)"
        if previous["attraction_id"] is not None:
            columns["테마유사도"] = "테마 유사도"
        columns["추천점수"] = "추천 점수"
        st.dataframe(result[list(columns)].rename(columns=columns).round(2), hide_index=True)
        st.caption("거리는 좌표로 계산한 값이며 실제 도로 이동거리와 다릅니다.")
    with st.expander("추천 기준 보기"):
        st.write(f"기준 관광지가 있으면 테마 유사도 {THEME_WEIGHT:.0%}, 거리 점수 {DISTANCE_WEIGHT:.0%}로 계산합니다. 기준 관광지가 없으면 가까운 순으로 추천합니다.")
        st.write("날씨 필터를 쓰면 적합 후보가 우선입니다. 보통 후보 보충을 선택한 경우에만 부족한 자리를 채웁니다.")
        st.caption("가중치는 초기 테스트 기준이며 결과를 보면서 조정할 예정입니다.")
