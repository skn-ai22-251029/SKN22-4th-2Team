# API 500 오류 근본 원인 분석 및 수정 보고서

- **일시**: 2026-02-27
- **분류**: Backend / Dockerfile 권한 버그
- **심각도**: 🔴 Critical (전체 API 502/500 차단)

---

## 🔍 오류 재현 경로 (에러 체인)

```
CloudWatch 로그 (short-cut-api, 2026-02-27 23:35)
↳ [SecurityMiddleware] Unexpected error: [Errno 13] Permission denied: '/home/appuser'
  ↳ middleware.py:95 → except Exception → 500 반환
```

**SecurityMiddleware가 문제처럼 보이지만, 실제 오류는 하위 레이어에서 발생.**

---

## 🐛 근본 원인 (Root Cause) — 3중 구조

### 원인 1: `/home/appuser` 홈 디렉토리 부재 (PRIMARY)

| 항목 | 내용 |
|---|---|
| **위치** | `Dockerfile` 65번째 줄 |
| **문제 코드** | `--no-create-home` 옵션으로 appuser 생성 |
| **원인** | Python `tempfile` 모듈이 임시 파일 경로 결정 시 `HOME` 환경 변수 → `/home/appuser`를 탐색하는데, 해당 폴더가 존재하지 않아 `[Errno 13] Permission denied` 발생 |
| **트리거** | `secrets_manager.py`의 `_handle_gcp_credentials()` 함수가 `tempfile.NamedTemporaryFile()`을 호출 |

### 원인 2: `src/data/history.db` SQLite 쓰기 권한 누락

| 항목 | 내용 |
|---|---|
| **위치** | `src/history_manager.py:10` |
| **문제 코드** | `DB_PATH = Path(__file__).parent / "data" / "history.db"` |
| **원인** | `/app/src/data/` 디렉토리가 `chown` 대상에는 포함되었으나, 해당 디렉토리 자체가 빌드 타임에 존재하지 않아 mkdir 실패 → 컨테이너 기동 시 초기화 실패 |

### 원인 3: `src/logs/` 로그 디렉토리 쓰기 권한 누락

| 항목 | 내용 |
|---|---|
| **위치** | `src/config.py:297-302` |
| **문제 코드** | `LoggingConfig.__post_init__` → `Path(log_file).parent.mkdir(parents=True, exist_ok=True)` |
| **원인** | `/app/src/logs/` 디렉토리 생성 권한 없음 |

---

## ✅ 수정 내용 (`Dockerfile`)

```diff
-# addgroup/adduser를 사용해 UID=1001 appuser로 실행
-RUN groupadd --gid 1001 appgroup \
-    && useradd --uid 1001 --gid appgroup --no-create-home --shell /bin/false appuser \
-    && chown -R appuser:appgroup /app

+# 런타임에 필요한 쓰기 가능 디렉토리 미리 생성
+# history_manager.py → /app/src/data/history.db
+# config.py LoggingConfig → /app/src/logs/
+RUN mkdir -p /app/src/data /app/src/logs
+
+# - 홈 디렉토리(/home/appuser) 생성: tempfile 등이 홈 디렉토리를 탐색하므로 필수
+RUN groupadd --gid 1001 appgroup \
+    && useradd --uid 1001 --gid appgroup \
+       --home /home/appuser --create-home \
+       --shell /bin/false appuser \
+    && chown -R appuser:appgroup /app /home/appuser
```

---

## 📋 PM 및 DevOps 전달용 메시지

### DevOps 에이전트에게 전달할 사항
- **현재 ECS에 배포된 이미지는 이 버그를 포함합니다.** `Dockerfile`이 수정되었으므로 **ECR 이미지 재빌드 후 ECS 서비스 재배포**가 필요합니다.
- 재배포 후 CloudWatch에서 `Permission denied` 에러가 사라지는지 확인해주세요.

### PM 에이전트에게 전달할 상태 업데이트
- **완료**: API 500 오류의 근본 원인(Dockerfile 권한 누락) 파악 및 코드 패치 완료
- **다음 단계**: DevOps 재배포 후 운영 환경 검증 필요
- **위험 사항**: SQLite 기반 `history.db`는 컨테이너 재시작 시 데이터 소실됨 → Issue #23 (DB 영속화) 우선순위 상향 권장

---

## ⏭️ 다음 단계 권장 사항

1. **DevOps**: 수정된 Dockerfile로 ECR 재빌드 → ECS 롤링 업데이트
2. **Backend (중기)**: `history.db` SQLite → EFS 마운트 또는 RDS 마이그레이션 (Issue #23)
3. **Backend (단기)**: `HistoryManager` 초기화 실패가 전체 앱 기동을 막지 않도록 graceful degradation 처리 추가 권장
