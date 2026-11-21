from html import escape
from datetime import date, time, datetime

import pandas as pd

import streamlit as st

from src.attractions import DATA_PATH, load_attractions
from src.recommend import THEME_WEIGHT, DISTANCE_WEIGHT, recommend_attractions


# 1. 페이지 설정
st.set_page_config(
    page_title="NUBI | 나에게 맞는 여행",
    page_icon="🌿",
    layout="wide",
)

# 고정된 디자인만 HTML/CSS로 작성한다.
# CSV에서 가져온 글자는 아래에서 escape()로 처리한다.
st.markdown(
    """
    <style>
    :root {
        --green: #194c3b;
        --cream: #f8f6f2;
        --line: #deded5;
    }

    .stApp {
        background: var(--cream);
        color: #17251e;
    }

    .block-container {
        max-width: 1440px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #173d30;
    }

    .brand {
        color: #194c3b;
        font-family: Georgia, serif;
        font-size: 3rem;
        font-weight: bold;
        line-height: 1;
    }

    .brand-caption {
        margin-top: 8px;
        color: #73796f;
        font-size: 0.85rem;
        letter-spacing: 0.08em;
    }

    .hero {
        margin: 20px 0 30px;
        padding: 42px;
        border: 1px solid #dbe2d7;
        border-radius: 24px;
        background: linear-gradient(
            115deg,
            #f4f3e9 10%,
            #e4ecdf 65%,
            #c9ddce 100%
        );
    }

    .hero-label {
        color: #38614d;
        letter-spacing: 0.23em;
        font-size: 0.8rem;
        font-weight: bold;
    }

    .hero-title {
        margin: 14px 0;
        font-size: clamp(2rem, 4vw, 3.4rem);
        font-weight: 750;
        line-height: 1.25;
        letter-spacing: -0.05em;
    }

    .hero-description {
        color: #59665c;
        font-size: 1.05rem;
    }

    .region-heading {
        margin-bottom: 8px;
        color: #244b38;
        font-size: 1.5rem;
        font-weight: bold;
    }

    .section-label {
        border-left: 4px solid #245741;
        padding-left: 12px;
        margin: 26px 0 16px;
        font-size: 1.3rem;
        font-weight: bold;
    }

    .place-card {
        border: 1px solid #deded5;
        border-radius: 18px;
        overflow: hidden;
        background: #fffdf9;
        transition: transform 180ms ease, box-shadow 180ms ease;
    }

    .place-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 24px rgba(25, 76, 59, 0.09);
    }

    .place-art {
        height: 115px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3rem;
        background: linear-gradient(135deg, #e9eee0, #c5d9cb);
    }

    .place-info {
        padding: 16px;
        min-height: 115px;
    }

    .place-title {
        font-weight: bold;
        font-size: 1.05rem;
        margin-bottom: 8px;
    }

    .place-detail {
        color: #6b756d;
        font-size: 0.86rem;
    }

    .ai-title {
        color: #194c3b;
        font-size: 1.65rem;
        font-weight: bold;
        margin-bottom: 8px;
    }

    .ai-note {
        color: #727a72;
        font-size: 0.9rem;
        margin-bottom: 20px;
    }

    .ai-message {
        padding: 18px;
        border-radius: 18px;
        background: #edf0e7;
        color: #304638;
        line-height: 1.7;
        margin-bottom: 20px;
    }

    .stButton > button {
        border-radius: 12px;
        border: 1px solid #cbd7cd;
        transition: background 180ms ease;
    }

    .stButton > button:hover {
        border-color: #194c3b;
        color: #194c3b;
        background: #edf2e9;
    }

    @media (prefers-reduced-motion: reduce) {
        .place-card,
        .stButton > button {
            transition: none;
        }

        .place-card:hover {
            transform: none;
        }
    }

    @media (max-width: 640px) {
        .hero {
            padding: 26px 22px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 2. 관광지 데이터와 화면 상태
@st.cache_data
def get_attractions():
    return load_attractions().copy()

attractions = get_attractions()

# 현재 CSV의 "(고성)봉포해변" 같은 이름에서 지역을 추출한다.
# 별도 지역 컬럼을 정리하면 그 컬럼을 사용하도록 바꾸면 된다.
attractions["지역"] = (
    attractions["관광지명"]
    .str.extract(r"^\(([^)]+)\)", expand=False)
    .fillna("기타")
)

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



regions = sorted(attractions["지역"].unique())

if "explore_region" not in st.session_state:
    st.session_state.explore_region = (
        "속초" if "속초" in regions else regions[0]
    )

if "design_recommendations" not in st.session_state:
    st.session_state.design_recommendations = None

if "design_recommendation_source" not in st.session_state:
    st.session_state.design_recommendation_source = None

if "visible_places" not in st.session_state:
    st.session_state.visible_places = 6

theme_icons = {
    "자연/힐링": "🌿",
    "캠핑/스포츠": "🏕️",
    "종교/역사/전통": "🏛️",
    "문화/예술": "🎨",
    "체험/학습/산업": "🔎",
    "쇼핑/놀이": "🛍️",
}


def change_region(region):
    st.session_state.explore_region = region
    st.session_state.visible_places = 6


def find_alternatives(place_id, place_name):
    """실제 추천 함수를 호출하고 결과를 화면 상태에 보관한다."""
    try:
        result = recommend_attractions(
            attraction_id=place_id,
            top_n=5,
            max_distance_km=30,
        )

        st.session_state.design_recommendations = result
        st.session_state.design_recommendation_source = place_name

    except ValueError as error:
        st.error(str(error))


# 3. 상단 로고와 메뉴
logo, menu = st.columns([1, 3])

with logo:
    st.markdown(
        """
        <div class="brand">nubi.</div>
        <div class="brand-caption">TRAVEL WITH NUBI</div>
        """,
        unsafe_allow_html=True,
    )

with menu:
    page = st.radio(
        "메뉴",
        ["지역 탐색", "내 여행", "NUBI AI"],
        horizontal=True,
        label_visibility="collapsed",
    )

st.divider()


# 4. 지역 탐색 화면
if page == "지역 탐색":
    st.markdown(
        """
        <div class="hero">
            <div class="hero-label">TRAVEL WITH NUBI</div>
            <div class="hero-title">여행의 새로운 방향을 찾다</div>
            <div class="hero-description">
                지역을 선택하고, 나에게 맞는 여행을 발견하세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    explore, assistant = st.columns([1.65, 1], gap="large")

    with explore:
        region = st.session_state.explore_region

        st.markdown(
            '<div class="region-heading">어디로 떠나볼까요?</div>',
            unsafe_allow_html=True,
        )
        st.caption("현재 관광지 데이터에 있는 지역을 선택할 수 있어요.")

        # 정확한 행정구역 지도 대신 실제 동작하는 지역 버튼부터 구현
        region_columns = st.columns(4)

        for index, region_name in enumerate(regions):
            with region_columns[index % 4]:
                selected = region_name == region

                st.button(
                    region_name,
                    key=f"region_{region_name}",
                    type="primary" if selected else "secondary",
                    on_click=change_region,
                    args=(region_name,),
                )

        st.caption("디자인 초안: 이 지역 선택 영역은 추후 지도 형태로 바꿀 예정입니다.")

        theme = st.selectbox(
            "관심 있는 여행 테마",
            ["전체"] + sorted(attractions["테마명"].dropna().unique()),
        )

        places = attractions[attractions["지역"] == region]

        if theme != "전체":
            places = places[places["테마명"] == theme]

        st.markdown(
            f'<div class="section-label">'
            f'{escape(region)} 추천 여행지</div>',
            unsafe_allow_html=True,
        )

        st.caption(
            f"{len(places)}곳을 살펴볼 수 있어요. "
            "사진 대신 테마 아이콘을 사용한 디자인 초안입니다."
        )

        if places.empty:
            st.info("선택한 테마에 해당하는 관광지가 없습니다.")

        card_columns = st.columns(3)

        for index, (_, place) in enumerate(
            places.head(st.session_state.visible_places).iterrows()
        ):
            place_id = place["관광지ID"]
            place_name = place["관광지명"]
            place_theme = place["테마명"]
            icon = theme_icons.get(place_theme, "📍")

            with card_columns[index % 3]:
                st.markdown(
                    f"""
                    <div class="place-card">
                        <div class="place-art">{icon}</div>
                        <div class="place-info">
                            <div class="place-title">
                                {escape(str(place_name))}
                            </div>
                            <div class="place-detail">
                                {escape(str(place_theme))} ·
                                {escape(str(place["실내구분"]))}
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("대체 장소 찾기", key=f"recommend_{place_id}"):
                    find_alternatives(place_id, place_name)

                if st.button("내 여행에 담기", key=f"save_{place_id}"):
                    st.session_state.itinerary.append({
                        "날짜": date.today().isoformat(), "시간": "10:00",
                        "관광지ID": place_id, "관광지명": place_name,
                    })
                    st.session_state.editor_version += 1
                    clear_result()
                    st.success("내 여행에 담았습니다. 내 여행에서 날짜와 시간을 수정해 주세요.")

                st.write("")

        if len(places) > st.session_state.visible_places:
            if st.button("여행지 더 보기"):
                st.session_state.visible_places += 6
                st.rerun()

    # 5. AI와 추천 결과 영역
    with assistant:
        with st.container(border=True):
            st.markdown(
                '<div class="ai-title">✦ NUBI AI</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="ai-note">나에게 맞는 여행을 함께 찾아요</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="ai-message">
                    마음에 드는 관광지의 ‘대체 장소 찾기’를 눌러보세요.<br>
                    비슷한 테마와 거리를 고려해 후보를 보여드릴게요.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(
                "AI 대화는 연결 준비 중입니다. "
                "아래 추천은 기존 Python 알고리즘의 계산 결과입니다."
            )

            result = st.session_state.design_recommendations
            source = st.session_state.design_recommendation_source

            if result is not None:
                st.subheader("대체 관광지")
                st.write(f"기준 관광지: {source}")
                st.caption("30km 이내 · 테마와 거리 반영 · 날씨 미반영")

                if result.empty:
                    st.info("30km 이내에 추천할 후보가 없습니다.")
                else:
                    for rank, (_, candidate) in enumerate(
                        result.iterrows(), start=1
                    ):
                        with st.container(border=True):
                            st.markdown(
                                f"**{rank}. {candidate['관광지명']}**"
                            )
                            st.write(
                                f"{candidate['테마명']} · "
                                f"{candidate['실내구분']}"
                            )
                            st.caption(
                                f"거리 {candidate['거리_km']:.2f}km · "
                                f"추천 점수 {candidate['추천점수']:.2f}"
                            )

            st.text_input(
                "NUBI에게 물어보기",
                placeholder="Gemini 연결 후 대화할 수 있어요.",
                disabled=True,
            )

        st.caption("거리와 실내외 정보는 현재 CSV를 기준으로 표시합니다.")


# 6. 일정 입력, 수정과 대체 관광지 추천
elif page == "내 여행":
    if "trip_notice" in st.session_state:
        st.success(st.session_state.pop("trip_notice"))
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

    # 추천을 적용할 때도 현재 조건과 일정이 같은지 확인한다.
    if result is not None and not result.empty and schedule_context is not None and context == saved:
        choices = result["관광지ID"].tolist()
        replacement = st.selectbox("일정에 넣을 대체 관광지", choices, format_func=labels.get)
        if st.button("선택한 관광지로 일정 변경"):
            index = schedule_context[0]
            st.session_state.itinerary[index].update({
                "관광지ID": replacement, "관광지명": names[replacement],
            })
            st.session_state.editor_version += 1
            clear_result()
            st.session_state.trip_notice = "날짜와 시간을 유지하고 관광지를 변경했습니다."
            st.rerun()


# 7. AI 전용 화면
else:
    st.header("✦ NUBI AI")
    st.write("여행 일정을 이해하고 변경 이유를 설명하는 기능을 준비하고 있어요.")
    st.info(
        "아직 Gemini와 날씨 API는 연결하지 않았습니다. "
        "지금은 ‘지역 탐색’에서 실제 추천 결과를 확인할 수 있습니다."
    )
    st.text_input(
        "여행 질문",
        placeholder="예: 속초 일정에서 실내 관광지를 추천해줘",
        disabled=True,
    )