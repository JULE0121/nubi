# NUBI — 날씨에 맞춰 지키는 여행 일정

날씨에 맞춰 여행 일정을 조정하고 대체 관광지를 추천하는 대학교 과제 프로젝트입니다.

## 목표
여행 일정 입력 → AI 일정 인식 → 사용자 확인·수정 → 날씨 적합도 판단 → 유사 관광지 추천 → AI 일정 재구성.
KNIME은 날씨 적합도와 관광지 유사도를 분석하고, Python은 분석 결과·거리 등을 이용해 추천 순위를 계산합니다.

## 현재 상태
폴더와 Streamlit 시작 화면만 준비했습니다. 실제 데이터, KNIME 워크플로우, 추천 알고리즘, GPT·날씨·지도 API 연동은 아직 없습니다.

## 폴더
- `data/raw/`: 출처를 기록한 원본 관광지·날씨·방문객 자료
- `data/processed/`: KNIME 정리·분석 결과
- `knime/`: KNIME 워크플로우
- `src/`: Python 추천 및 API 연결 코드
- `docs/`: 개발 순서와 설계 기록
- `app.py`: Streamlit 시작 화면

## 실행
Python 환경에 의존성을 설치한 뒤 실행합니다. 가상환경을 만든 뒤 의존성을 설치합니다.

```bash
cd ~/jule/nubi
python3 -m venv ~/.venvs/nubi
source ~/.venvs/nubi/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

API 키는 `.env`에 저장하고 Git에 추가하지 않습니다.

## 다음 작업
`docs/roadmap.md`의 03단계부터 자료의 출처와 분석 단위를 정합니다. 교수님의 원본 과제 안내·평가기준을 확인하여 제출 범위를 확정합니다.
