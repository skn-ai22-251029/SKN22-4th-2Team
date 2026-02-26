# Issue #14 - 이중 LLM 호출 비용 절감 및 스트리밍 응답 최적화

## 📅 작업일: 2026-02-26

## 🛠️ 작업 내용

### 문제점
`src/analysis_logic.py` Step 5(143~150행)에서 **동일한 입력으로 GPT-4o를 2번** 연속 호출하는 구조:

| 호출 | 메서드 | 모델 | 출력 | 비용 (추정) |
|------|--------|------|------|------------|
| 1차 | `critical_analysis_stream()` | GPT-4o | 스트리밍 마크다운 | ~$0.015 |
| 2차 | `critical_analysis()` | GPT-4o | JSON 구조화 | ~$0.015 |
| **합계** | | | | **~$0.03/분석** |

### 해결 방안
2차 GPT-4o 호출을 **GPT-4o-mini 경량 파싱**으로 교체:

| 호출 | 메서드 | 모델 | 출력 | 비용 (추정) |
|------|--------|------|------|------------|
| 1차 | `critical_analysis_stream()` (유지) | GPT-4o | 스트리밍 마크다운 | ~$0.015 |
| 2차 | `parse_streaming_to_structured()` (신규) | **GPT-4o-mini** | JSON 변환 | ~$0.0003 |
| **합계** | | | | **~$0.0153/분석** |

→ **약 50% 비용 절감** 달성

### 변경 파일

#### `src/patent_agent.py`
- `PARSING_MODEL` 환경변수 추가 (`gpt-4o-mini` 기본값)
- `parse_streaming_to_structured()` 메서드 추가:
  - 스트리밍 마크다운 텍스트를 GPT-4o-mini로 JSON 구조 변환
  - 타임아웃 30초 설정
  - try-except 예외 처리 + `_empty_analysis()` 폴백
  - Hallucination 방지: "보고서에 명시된 정보만 추출" 지시어 포함

#### `src/analysis_logic.py`
- 150행: `agent.critical_analysis()` → `agent.parse_streaming_to_structured()` 교체

### 보존된 기존 코드
- `critical_analysis()` 메서드 자체는 **삭제하지 않음** (독립 파이프라인 `analyze()`에서 사용 중)
- `critical_analysis_stream()` 스트리밍 로직은 변경 없음

## ✅ 검증 결과
- Python AST 구문 검증: `patent_agent.py` OK, `analysis_logic.py` OK
- `critical_analysis` 메서드의 다른 호출처(`analyze()`) 보존 확인 완료

## 📌 다음 단계 권장 사항
1. Streamlit 앱 실행하여 실제 분석 흐름 정상 동작 확인
2. OpenAI API 사용량 대시보드에서 호출 횟수 감소 확인

## 📋 PM 에이전트 전달용 상태 업데이트
- **Issue #14**: 코드 수정 완료, 배포 후 실제 환경 검증 필요
- **변경 범위**: `src/patent_agent.py`, `src/analysis_logic.py` (2개 파일)
- **리스크**: 낮음 (기존 메서드 보존, 폴백 로직 구현)
