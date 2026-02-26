# 06. `config.py` NameError 버그 수정 — 전방 참조(Forward Reference) 제거

**작업 일시**: 2026-02-25  
**담당**: Backend 에이전트  
**관련 파일**: `src/config.py`

---

## 🐛 버그 요약

| 항목 | 내용 |
|------|------|
| **에러 종류** | `NameError: name 'update_config_from_env' is not defined` |
| **발생 위치** | `src/config.py` 329번 줄 |
| **영향 범위** | 컨테이너 기동 시 `import src.config` 자체가 실패 → ECS 서비스 배포 불가 |

## 🔍 원인 분석

Python은 스크립트를 **위에서 아래로 순차 실행**합니다.  
329번 줄에서 `update_config_from_env()`를 호출했지만, 함수는 336번 줄(현재 기준)에서 정의되었기 때문에 모듈 임포트 시점에 `NameError`가 발생했습니다.

```python
# 수정 전 (버그 있음)
config = PatentGuardConfig()
update_config_from_env()        # ← 329번 줄: 아직 미정의 함수 호출 ❌

def update_config_from_env() -> PatentGuardConfig:   # ← 336번 줄
    ...
```

## ✅ 수정 내용

```diff
# src/config.py

 config = PatentGuardConfig()
-update_config_from_env()   # ← 전방 참조 호출 삭제

 def update_config_from_env() -> PatentGuardConfig:
     ...
     return config

+# bootstrap_secrets() 이후 환경 변수가 주입된 상태에서 config를 최신화
+update_config_from_env()   # ← 함수 정의 이후로 이동 ✅
```

**변경 요점**:
1. **삭제**: 329번 줄의 전방 참조 호출 제거
2. **추가**: `update_config_from_env()` 함수 정의 직후(return 다음 줄)에 호출 이동
3. **주석 추가**: 호출 목적을 한국어로 명시 (`bootstrap_secrets()` 이후 환경 변수 최신화)

## 🔄 실행 순서 (수정 후)

```
모듈 임포트 시
  1. bootstrap_secrets()         ← AWS Secrets Manager or .env 에서 환경 변수 주입
  2. config = PatentGuardConfig() ← dataclass 기본값으로 인스턴스 생성
  3. def update_config_from_env() ← 함수 정의
  4. update_config_from_env()    ← 환경 변수 → config 필드에 반영 ✅
```

## 📌 다음 단계 권장 사항

- DevOps 에이전트: 이 수정 사항이 포함된 상태로 **ECS 서비스 재배포** 진행 가능
- `main.py` 임포트 시 더 이상 `NameError`가 발생하지 않으므로 컨테이너 정상 기동 예상
