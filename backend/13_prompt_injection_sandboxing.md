# 🛡️ Prompt Injection Sandboxing 구현 보고서

## 📋 작업 개요
사용자 입력에 의한 Prompt Injection 공격을 방어하고, LLM 시스템 프롬프트를 보호하기 위한 보안 샌드박싱 레이어를 구현하였습니다.

## 🛠️ 주요 변경 사항

### 1. 보안 모듈 신규 구현 (`src/security.py`)
- **위험 패턴 탐지**: `"ignore previous instructions"`, `"시스템 프롬프트 무시"` 등 주요 인젝션 키워드 및 문장을 탐지하는 정규식 필터링 적용.
- **입력 길이 제한**: 최대 2,000자로 입력을 제한하여 리소스 소모 및 버퍼 오버플로우성 공격 방어.
- **이스케이핑 처리**: HTML 이스케이핑을 통해 `<script>` 태그 등 악의적인 구조 삽입 방지.
- **구조적 분리 래퍼**: 사용자 입력을 `<user_query>` 태그로 감싸 시스템 지시어와의 경계를 명확히 구분.

### 2. RAG 파이프라인 통합 (`src/patent_agent.py`)
- `PatentAgent.analyze()`: 최상위 진입점에서 모든 사용자 아이디어 샌드박싱 처리.
- **프롬프트 템플릿 업데이트**: 
  - `generate_hypothetical_claim`, `generate_multi_queries`, `grade_results`, `rewrite_query`, `_build_analysis_prompts`, `critical_analysis_stream` 등 모든 LLM 호출 구간에서 사용자 입력을 보안 래퍼로 감싸도록 수정.

### 3. 탐지 로깅 및 예외 처리
- 위험 패턴 탐지 시 `WARNING` 레벨 로그를 기록하며, 상세 원본 데이터는 마스킹 처리하여 로그 노출 방지.
- `PromptInjectionError` 커스텀 예외를 정의하여 상위 레이어(API/CLI)에서 적절한 에러 메시지를 반환할 수 있도록 설계.

### 4. 단위 테스트 검증 (`tests/test_security.py`)
- 정상 입력 처리 확인.
- 길이 제한 초과 시 거부 확인.
- 다양한 한글/영문 인젝션 패턴 탐지 성능 검증.
- HTML 이스케이핑 정상 작동 확인.

## 🔐 보안 고려사항
- 정규식 필터와 화이트리스트 성격의 구조적 분리(Tagging)를 병행하여 방어력 강화.
- `AsyncOpenAI` 호출 시 구조적으로 `user` 역할을 엄격히 분리하여 사용.

## ✅ 다음 단계 권장 사항
- **FastAPI 통합**: 현재 구현된 보안 레이어를 FastAPI의 `Depends` 또는 미들웨어 수준으로 확장하여 모든 엔드포인트에 일관되게 적용.
- **패턴 고도화**: 운영 중 발견되는 새로운 인젝션 기법을 지속적으로 `DANGEROUS_PATTERNS`에 업데이트.
