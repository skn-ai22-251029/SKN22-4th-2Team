# 사용자 세션(식별) 관리 및 API Rate Limiting 정책 기획

## 📋 개요
사용자별 무분별한 API 호출을 방지하고 OpenAI/Pinecone 등 클라우드 API의 과금 폭탄을 예방하기 위해, 클라이언트 식별 체계와 Rate Limiting(사용량 제한)을 기획합니다. 안정적인 서비스 운영과 악의적 봇 공격을 방어하기 위한 백엔드 아키텍처 관점의 설계입니다.

## 🎯 설계 내용

### 1. 사용자 식별 방식 결정
- **채택 방식:** **비로그인 기반 고유 세션(UUID) 발급 + IP 주소 보조 식별**
- **상세 내용:** 
  - 아직 정식 로그인이 도입되지 않은 상태를 가정하여, 사용자가 최초 접속 시 프론트엔드/백엔드에서 고유한 Session ID (UUID v4)를 생성합니다.
  - 이 Session ID를 브라우저의 로컬 스토리지(Local Storage) 혹은 쿠키(Cookie)에 저장하여 후속 요청 시 헤더(`X-Session-ID`)에 포함시킵니다.
  - **IP 주소:** 다중 브라우저 탭 및 시크릿 모드를 악용하는 봇을 차단하기 위해 IP 주소 기반의 Rate Limit도 보조적으로 병행합니다. (단, NAT 환경을 고려하여 IP + Session ID 조합으로 식별)

### 2. 사용량 제한 (Rate Limiting) 정책
- **기준:** 
  - **1일 기준:** 사용자(Session ID) 당 최대 10회 분석 허용
  - **1시간 기준:** 사용자(Session ID) 당 최대 5회 분석 허용
  - **IP 기준 (Bot 방어):** 특정 IP에서 1분 내 20회 이상 호출 시 10분간 차단 (IP-level Throttling)
- **구현 방식:** 
  - Redis를 활용한 단기 메모리 저장소에 `rate_limit:session:{session_id}:YYYYMMDD` 혹은 `rate_limit:ip:{ip_address}:YYYYMMDD` 형태의 키를 구성하여 카운트(TTL 설정)합니다.
  - FastAPI의 의존성 주입(Dependency Injection)을 통해 엔드포인트 진입 전 미들웨어에서 검증합니다.

### 3. Rate Limit 초과 시 UI/UX 에러 메시지 설계
- **HTTP Status Code:** `429 Too Many Requests`
- **사용자 노출 메시지:**
  - 1시간 기준 초과 시: "단기 분석 요청이 너무 많습니다. 잠시 후 1시간 뒤에 다시 시도해주세요."
  - 1일 기준 초과 시: "일일 무료 분석 횟수(10회)를 모두 소진했습니다. 내일 다시 이용해주세요!"
  - IP 차단 시: "비정상적인 트래픽이 감지되어 일시적으로 이용이 제한되었습니다."
- **Response JSON:**
  ```json
  {
    "detail": "Rate limit exceeded",
    "message": "일일 무료 분석 횟수(10회)를 모두 소진했습니다. 내일 다시 이용해주세요!",
    "reset_time": "2026-02-27T00:00:00+09:00"
  }
  ```

### 4. 검색 히스토리 조회를 위한 세션-데이터 매핑 구조
- **데이터베이스 스키마(Logical Diagram):**
  - **Entity `UserSession`:** `session_id` (PK, UUID), `created_at`, `last_accessed_at`, `ip_address`
  - **Entity `SearchHistory`:** `id` (PK), `session_id` (FK), `query_text` (사용자 질의), `ai_response` (AI 분석 결과), `created_at`
- **로직:**
  - 사용자가 앱을 재방문 시 프론트엔드가 저장된 `Session ID`를 함께 전송.
  - 백엔드는 DB(또는 Redis)에서 `SearchHistory`를 `session_id`로 조회하여 과거 내역 목록 반환.
  - 필요시 Session TTL (예: 30일 접속 없을 시 기록 삭제) 정책으로 데이터 용량 최적화.

## 📌 기대 효과
- 무단 트래픽 및 봇(Bot) 공격 원천 방어 및 API 토큰 남용 방지
- 악의적인 시나리오 차단으로 서비스 안정성 보장
- 추후 정식 회원가입/로그인(OAuth) 도입 시 기존 세션 히스토리를 사용자 계정으로 원활히 마이그레이션 가능
