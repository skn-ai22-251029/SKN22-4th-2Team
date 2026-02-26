# RAG 로직 고도화: LLM 환각(Hallucination) 통제

이 사항은 **이슈 #2 (RAG 고도화 — LLM 환각 통제)**를 처리하기 위해 수행된 내용입니다. `src/patent_agent.py`에 구현되어 있던 `grade_results`, `_build_analysis_prompts`, `critical_analysis_stream` 메서드 등의 시스템 프롬프트를 전면 개편하였습니다.

## 🛠️ 코드베이스 분석 및 반영 결과 (문제점 및 개선 방향)
1. **문제점**: 
   - 기존의 특허 유사도/침해 분석 프롬프트는 LLM이 지닌 내부 지식을 활용하여 정보의 틈새를 창의적으로 유추/메우려는 속성이 강했습니다 (Hallucination 유발).
   - "A 기능이 없지만, B로 대체할 수 있을 것 같으므로 침해 리스크 높음"과 같은 모호하거나 잘못된 판정을 내릴 위험이 존재했습니다.
2. **해결 및 개선사항**:
   - **Strict Grounding (사실 기반 평가)**: 프롬프트 최상단에 `[Context]에 제공된 텍스트의 문언에만 근거하라`는 원칙을 **CRITICAL** 지시어로 강하게 부여했습니다.
   - **판단 기준표(Rubric) 명확화**: 점수를 매기는 `grade_results`에서 `0.0` 점의 조건을 명시하고, 기술 분야가 동일하더라도 세부 구성요소가 없으면 낮은 점수를 부여하게 기준을 조였(stiffen)습니다.
   - **Explicit Citation (인용 의무화)**: 출력 시 반드시 `[출처: 특허번호]`를 병기하도록 지시하였고, Few-shot 예시를 추가하여 인용 없는 주장을 스스로 차단하게 만들었습니다. 
   - **"정보 없음" 선언 강제**: Context에 정보가 없으면 추측하지 말고 "해당 구성요소는 선행 특허에서 조회되지 않음"이라고 선언하도록 명시했습니다.

## 📋 PM 및 DevOps 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: RAG 로직 고도화 (Backend)**
  - [x] LLM 시스템 프롬프트 Strict Grounding 요건 강화 
  - [x] 판정 Rubric 명확화 및 Few-Shot 예시 삽입
- **Epic: FastAPI 웹 서비스화 (Backend) -> 다음 단계**
  - [ ] 메인 라우터(`main.py`) 및 API 엔드포인트 뼈대 작성
  - [ ] Pydantic Model 스키마 정의 및 RESTful API 구현
  - [ ] CORS / ErrorHandler 미들웨어 추가
