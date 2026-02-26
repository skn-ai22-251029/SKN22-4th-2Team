# 🚀 빌드 레이어 캐시 및 태깅 전략 최적화 적용 내역 (Issue #7 잔여)

**날짜**: 2026-02-26  
**관련 작업**: Issue #7 (GitHub Actions CI/CD 최적화 부분)  
**상태**: ✅ 완료

---

## 🔧 주요 변경 사항

### 1. `docker/metadata-action` 도입 (태깅 자동화)
기존에는 쉘 스크립트(`echo "${{ github.sha }}" | cut -c1-7`)를 통해 수동으로 이미지 태그를 생성하고, `docker/build-push-action`에 하드코딩 형태로 주입했습니다. 이를 Docker 공식 메타데이터 액션으로 대체하여 관리를 자동화했습니다.

* **적용점**: Staging/Prod 모두 Step 6 추가 (`id: meta`)
* **태깅 규칙**:
  * **Staging (develop)**: 짧은 SHA 태그(`sha-최소 7자리`), `staging-latest` 태그, 브랜치명 태그 (`develop`)
  * **Production (main/v*)**: 짧은 SHA 태그, `latest` 태그, 브랜치명 태그(`main`), 시맨틱 태그 (v* 푸시 시 해당 버전 자동화)
* 💡 **참고**: GitHub SHA 태그가 기존 `1234abc` 형태로 덮어써지도록 `prefix=` 옵션을 명시하여 `sha-` 접두사가 붙지 않게 호환성을 유지했습니다.

### 2. 빌드 캐시 `scope` 추가 (레이어 충돌 방지)
파이프라인이 여러 브랜치에서 동시다발적으로 실행될 때, 로컬 Docker Buildx 캐시가 덮어씌워지거나 오염되는 문제를 방지하기 위해 각 캐시 전략에 **개별 스코프**를 지정했습니다.

* **이전 설정**: `cache-from: type=gha`, `cache-to: type=gha,mode=max` (모든 파이프라인에서 캐시 공유)
* **변경 설정**:
  ```yaml
  cache-from: type=gha,scope=${{ github.workflow }}-${{ github.ref_name }}
  cache-to: type=gha,mode=max,scope=${{ github.workflow }}-${{ github.ref_name }}
  ```
* 🎯 **효과**:
  * `develop` 브랜치 빌드는 `ecr-cicd-develop` 캐시 저장소만 참조/업데이트합니다.
  * `main` 브랜치 빌드는 `ecr-cicd-main` 캐시 저장소만 참조/업데이트합니다.
  * 안전하고 일관된 컨테이너 빌드 환경을 제공합니다.

---

## 🎉 마무리
이로써 Issue #7 (ECR CI/CD 파이프라인 구성)의 인프라스트럭처 연동 및 최적화가 완벽하게 마무리되었습니다! 백엔드 구성에 따라 ECS 배포 트리거만 연동되면 Full CI/CD가 수행됩니다.
