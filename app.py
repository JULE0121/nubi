"""NUBI 과제용 시작 화면. 외부 API를 호출하지 않습니다."""
import streamlit as st

st.set_page_config(page_title="NUBI", page_icon="🧭")
st.title("NUBI")
st.caption("날씨에 맞춰 지키는 나의 여행 일정")
st.write("계획한 여행 일정을 입력해 주세요.")
st.text_area("여행 일정", placeholder="예: 춘천에서 오전에는 산책하고 오후에는 전시를 보고 싶어요.")
st.button("AI로 일정 분석하기", disabled=True)
st.info("현재는 프로젝트 준비 단계입니다. 일정 인식과 관광지 추천 기능은 개발 예정입니다.")
