# [FastAPI] Streamlit 분리 및 Stateless 웹 서비스 구조 개편

## 1. 완료한 작업 내역
- `main.py` -> `embedding_test.py` 이름 변경 (기존 임베딩 테스트 스크립트 보존)
- 비즈니스 로직과 UI 구조 완전 분리 (`src/analysis_logic.py` 리팩토링)
  - 파라미터에서 UI 요소(`status_container`, `streaming_container`) 및 `st.session_state` 직접 의존을 제거
  - `AsyncGenerator` 기반으로, 실시간 진행 상황 이벤트와 AI의 텍스트 스트리밍 토큰을 반환(yield)하도록 구조 변경
- 새로운 `main.py`를 작성하여 **FastAPI 앱** 진입점 생성
  - 프론트엔드 연동을 위한 **CORS 미들웨어** 적용
  - `POST /api/v1/analyze`: SSE(Server-Sent Events) 프로토콜을 사용해 모델 스트리밍 응답을 내려줄 수 있도록 처리
  - `GET /api/v1/history/{user_id}`: HistoryManager를 사용해 특정 유저의 이력을 반환
- 기존 Streamlit 로직(`app.py`) 재작성
  - 리팩토링 된 `analysis_logic.py`를 사용하여 Streamlit에서도 `async for`로 이벤트를 수신받아 UI를 렌더링하도록 동기화 

## 2. 다음 단계 권장 사항
- FastAPI `uvicorn` 실행 후, OpenAPI Swagger 페이지 / API 응답(cURL) 수동 검증
- 컨테이너화를 통해 배포 가능하도록 `Dockerfile` 작성 (멀티 스테이지 빌드 기반 패키지 크기 축소)
- 외부 API 통신부(LLM)에 대한 Timeout 예외 처리 강화 지원 고려 (현재는 `src/patent_agent.py`가 관리중인지 점검이 필요함)

## 3. PM 에이전트 상태 업데이트 요약
1. **Epic: FastAPI 웹 서비스화 (Backend)**
   - API 라우터 뼈대(`main.py`) 작성 및 Streamlit 렌더링 코드 종속성 완전 분리 목표 달성
2. 다음 일정: 컨테이너 및 인프라 구축(Dockerfile 작성) 단계로 진행할 것을 권고합니다.
