# 🔍 API 500 에러 근본 원인 분석 보고서

> **일시**: 2026-02-28 02:24 KST  
> **증상**: `POST /api/v1/analyze` → 500 Internal Server Error  
> **영향**: 프론트엔드에서 분석 요청 시 `API 오류: 500` 에러 발생

---

## 1. 브라우저 콘솔 에러 분류

### ❌ 앱과 무관한 에러 (무시)

| 에러 | 원인 |
|------|------|
| `runtime.lastError: Could not establish connection` | Chrome 확장 프로그램 (MetaMask, Apollo DevTools 등) |
| `MetaMask extension not found` | MetaMask의 `inpage.js` 자동 주입 실패 |
| `Apollo DevTools` | Apollo GraphQL 개발자 도구 |
| `cdn.tailwindcss.com production warning` | TailwindCSS CDN 개발용 경고 |
| `favicon.ico 404` | 파비콘 파일 미존재 |

### 🚨 실제 문제

- `analyze:1 Failed to load resource: 500`
- `app.js:230 Analysis failed: Error: API 오류: 500`

---

## 2. 에러 발생 경로 추적

```
프론트엔드 (app.js:165)
  → POST /api/v1/analyze (JSON body)
    → src/api/main.py (create_app → include_router)
      → src/api/v1/router.py (analyze_patent)
        → analyze_service.py (process_analysis_stream)
          → PatentAgent.search_with_grading()
            → search_multi_query() → _execute_search()
              → PineconeClient.async_hybrid_search()
              → embed_text() → OpenAI API
```

**`router.py:42`** 의 `except Exception` 블록에서 500 HTTPException으로 변환됨.

---

## 3. 500 에러 근본 원인 후보

### 후보 1: 환경변수/시크릿 누락 (가장 유력)

- `.env` 파일이 없거나 `OPENAI_API_KEY`, `PINECONE_API_KEY` 미설정
- `PatentAgent.__init__()` L172: `config.embedding.api_key` 없으면 **ValueError** 즉시 발생
- `PineconeClient.__init__()` L182: `PINECONE_API_KEY` 없으면 **ValueError** 발생

### 후보 2: Pinecone 연결 실패

- 인덱스 이름(`patent-guard-hybrid`)이 실제 Pinecone 계정에 없는 경우
- API 키가 유효하지 않은 경우

### 후보 3: BM25Encoder 초기화 실패

- 이전 대화(78ae1167)에서 해결한 Permission denied 문제의 잔재
- 컨테이너 환경에서 HOME 디렉토리 쓰기 권한 문제 가능

### 후보 4: OpenAI API 호출 실패

- Rate limit 초과
- API 키 유효성 만료
- 네트워크 연결 문제

---

## 4. 확인 필요 사항

1. **실행 환경**: 로컬(`python main.py`) vs ECS 배포?
2. **`.env` 파일 존재 여부** 및 필수 키 설정 확인
3. **서버 터미널 로그** (uvicorn 콘솔 출력)

---

## 5. 다음 단계 권장 사항

- [ ] 서버 로그 확인하여 정확한 Exception 메시지 파악
- [ ] `.env` 파일 필수 키 검증
- [ ] 에러 메시지에 따라 해당 모듈 수정
