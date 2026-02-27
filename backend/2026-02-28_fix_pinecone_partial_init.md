# 🔧 PineconeClient 부분 초기화 버그 수정

> **일시**: 2026-02-28  
> **에러**: `'PineconeClient' object has no attribute 'bm25_params_path'`  
> **영향**: `/api/v1/analyze` → 500 Internal Server Error

---

## 근본 원인

`PineconeClient.__init__()` 에서 인스턴스 속성 초기화 순서가 잘못되어 있었음:

```
# 기존 순서 (위험)
L184: self.pc = Pinecone(api_key=...)         # ← 외부 API 호출 (실패 가능)
L188: self._ensure_index_exists()              # ← 외부 API 호출 (실패 가능)
L190: self.index = self.pc.Index(...)           # ← 외부 API 호출 (실패 가능)
L193: self.metadata = {}                        # 여기서부터 속성 설정
L199: self.bm25_params_path = ...               # ← 이 줄 도달 전 실패하면 속성 없음!
```

**Pinecone API 호출(L184~L190)이 실패하면 `bm25_params_path`, `metadata`, `bm25_encoder` 속성이 설정되지 않은 채로 `AttributeError` 발생.**

## 수정 내용

### 1. `src/vector_db.py` — 방어적 선초기화

모든 인스턴스 속성을 **외부 API 호출 전에** 안전한 기본값으로 먼저 설정:

```python
# 수정된 순서 (안전)
self.pc = None               # 기본값
self.index = None             # 기본값
self.metadata = {}            # 기본값
self.metadata_path = ...      # 기본값
self.bm25_params_path = ...   # 기본값
self.bm25_encoder = BM25Encoder()  # 빈 인코더

# 이제 외부 API 호출
self.pc = Pinecone(api_key=...)
self.index = self.pc.Index(...)
```
### 2. `src/api/dependencies.py` — 에러 추적 강화

`get_patent_agent()`에 try-except 추가하여 초기화 실패 시 정확한 에러 타입과 traceback을 로그에 기록.

## Pinecone 인덱스 상태 확인

| 항목 | 값 |
|------|-----|
| 인덱스 이름 | `patent-guard-hybrid` |
| 상태 | ✅ Ready |
| 벡터 수 | 20,739 |
| 네임스페이스 | `default` |
| Dimension | 1536 |
| Metric | dotproduct |

→ 인덱스 설정은 코드와 완벽히 일치. Pinecone 쪽 문제는 아님.

## 다음 단계

1. 이 코드를 push → CI/CD로 ECS 재배포
2. 배포 후 `/api/v1/analyze` 정상 응답 확인
3. 만약 여전히 에러 발생 시 → ECS 로그에 `exc_info=True` traceback이 찍히므로 정확한 원인 추적 가능
