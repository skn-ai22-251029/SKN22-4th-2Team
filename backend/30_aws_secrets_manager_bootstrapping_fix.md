### 🛠️ 코드베이스 분석 결과
ECS Fargate 배포 환경에서 AWS Secrets Manager 주입값이 늦게 들어오거나 로컬 `.env` 파일이 물리적으로 없는 환경에서 애플리케이션 시작(Bootstrapping) 시 `sys.exit(1)` 패닉 로직으로 인해 **CrashLoopBackOff** 현상이 발생할 여지가 있었습니다. 
이에 따라 `src/api/main.py` 파일 내 시크릿 체크 로직을 클라우드 네이티브 방식(Cloud-Native)으로 리팩토링했습니다. 물리적 `.env` 검사에 대한 가능성이나 포괄적 `try-except`/`sys.exit(1)` 기반의 강제 종료 로직을 걷어내고, 오직 OS에 최종 주입된 환경변수인 `os.getenv('OPENAI_API_KEY')` 값이 비어있는 경우에만 명확하게 `ValueError`를 발생시키도록 수정했습니다. 이는 컨테이너 환경의 Zero Hardcoding 및 보안 최우선 원칙을 완벽히 준수합니다.

### 📋 PM 및 DevOps 전달용 백로그 (복사해서 각 에이전트에게 전달하세요)
- **Epic: RAG 로직 고도화 및 배포 최적화 (Backend/PM)**
  - [x] **🚀 긴급 조치:** 물리적 `.env` 파일 검사 개념을 애플리케이션 초기화(Bootstrapping) 과정에서 완전히 배제
  - [x] OS 환경 변수인 `os.getenv('OPENAI_API_KEY')`의 유무만 확인하여 `ValueError` 패닉을 발생시키도록 `src/api/main.py` 리팩토링 완료
- **Epic: AWS 인프라 프로비저닝 (DevOps)**
  - [ ] AWS Secrets Manager 기반 비밀 값 등록 및 Task Definition의 `secrets` 매핑 구성 정상화 완료 점검 요청
