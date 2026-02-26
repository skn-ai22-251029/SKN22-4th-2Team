# 🔧 GitHub Actions Workflow – secrets 컨텍스트 오류 수정

**날짜**: 2026-02-26  
**파일**: `.github/workflows/ecr-cicd.yml`  
**상태**: ✅ 완료

---

## 📋 문제 요약

### 에러 메시지
```
Invalid workflow file
(Line: 211, Col: 9): Unrecognized named-value: 'secrets'.
Located at position 56 within expression:
  needs.build-and-push-production.result == 'success' && secrets.ECS_SERVICE_PROD != ''
```

### 근본 원인
GitHub Actions에서 **job-level `if` 표현식에는 `secrets` 컨텍스트를 사용할 수 없습니다.**
- `secrets`는 **step-level** (`steps.*.if`, `steps.*.env`, `steps.*.with`) 에서만 참조 가능
- `github`, `needs`, `vars`, `inputs` 등의 컨텍스트만 job-level `if`에서 허용됨

---

## ✅ 해결 방안

### 전략: Step Output으로 우회

`secrets` 값의 존재 여부를 **step에서 검사**하여 **job output으로 내보내고**, 하위 job에서 해당 output을 참조하는 방식으로 우회합니다.

### 변경 사항

#### 1. `build-and-push-production` job – output 추가 (Line 128)

```yaml
outputs:
  image-uri: ${{ steps.meta.outputs.image-uri }}
  image-tag: ${{ steps.meta.outputs.sha-tag }}
  ecs-deploy-enabled: ${{ steps.check-ecs.outputs.enabled }}  # 신규 추가
```

#### 2. `build-and-push-production` job – Secret 존재 검사 step 추가 (Step 8)

```yaml
- name: ECS 배포 설정 확인
  id: check-ecs
  run: |
    if [ -n "${{ secrets.ECS_SERVICE_PROD }}" ]; then
      echo "enabled=true" >> $GITHUB_OUTPUT
      echo "[CI] ECS 배포 활성화: ECS_SERVICE_PROD 설정됨"
    else
      echo "enabled=false" >> $GITHUB_OUTPUT
      echo "[CI] ECS 배포 비활성화: ECS_SERVICE_PROD 미설정"
    fi
```

#### 3. `deploy-ecs-production` job – if 조건 수정 (Line 226-228)

```yaml
# ❌ 수정 전 (에러 발생)
if: >
  needs.build-and-push-production.result == 'success' &&
  secrets.ECS_SERVICE_PROD != ''

# ✅ 수정 후 (output 참조)
if: >
  needs.build-and-push-production.result == 'success' &&
  needs.build-and-push-production.outputs.ecs-deploy-enabled == 'true'
```

---

## 📚 참고: GitHub Actions 컨텍스트 사용 가능 범위

| 위치 | 사용 가능한 컨텍스트 |
|------|---------------------|
| Job-level `if` | `github`, `needs`, `vars`, `inputs`, `strategy`, `matrix` |
| Step-level `if` | 위 모두 + `secrets`, `env`, `steps`, `job`, `runner` |
| Step-level `env`/`with` | 모든 컨텍스트 사용 가능 |

---

## 🔗 영향 받는 워크플로우 실행

- ❌ Workflow Run #1 ~ #4: 모두 `Invalid workflow file` 에러로 실패
- 수정 후 다음 push에서 정상 동작 예상
