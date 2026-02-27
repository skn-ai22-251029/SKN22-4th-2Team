### 🔍 총평 (Architecture Review)
Redis `redis.asyncio` 모듈과 Pipeline 트랜잭션을 활용해 Rate Limiting 아키텍처를 올바르게 구성했습니다. `main.py`의 미들웨어 의존성 주입(Dependency Injection)과 Redis 장애 시 'Fail-open(에러 무시 후 통과)' 처리 등은 실제 운영(Production) 환경에서 서비스 가용성을 보장하는 훌륭한 접근입니다. 다만 비동기 파이프라인(async-pipeline) 사용 시 치명적인 문법 오류가 존재합니다.

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**
- `src/rate_limiter.py:68~69, 85~88` - **비동기 Redis 파이프라인 `await` 오남용**
  - 원인: `redis.asyncio`의 `pipeline` 컨텍스트 내에서 개별 명령어(`pipe.incr()`, `pipe.expire()`)에 `await`를 사용하면 객체 타입 에러(`TypeError: object Pipeline can't be used in 'await' expression`)가 발생하여 애플리케이션에 예외가 발생합니다.
  - 해결: 아래와 같이 개별 명령어에는 `await`를 제거하고, 오직 마지막 `await pipe.execute()`에만 비동기로 실행되게 수정하세요.
    ```python
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(ip_key)
        pipe.expire(ip_key, 60)
        res = await pipe.execute()
    ```

**[🟡 Warning: 잠재적 위험 - 개선 권장]**
- `src/rate_limiter.py:69, 86, 88` - **만료 시간(TTL) 무한 연장 (Sliding Window Bug)**
  - 원인: 매 API 호출마다 `expire` 메서드가 호출되면 TTL이 60초 또는 지정 시간으로 갱신(Reset)됩니다. 악의적인 사용자가 59초 간격으로 요청을 보내면 IP Key가 만료되지 않고 무한 연장되어 억울하게 차단당하는 이슈가 생길 수 있습니다.
  - 해결: 코드를 `pipe.expire(ip_key, 60, nx=True)` 처럼 수정하여 최초 키 생성 시점에만 TTL이 적용되도록 방어 로직을 추가하는 것을 적극 권장합니다. (버전 호환 문제 시 `res[0] == 1`일 때만 `expire`하는 로직 등 대안 활용 가능)

**[🟢 Info: 클린 코드 및 유지보수 제안]**
- `src/main.py:12~30` - CORS의 `ALLOWED_ORIGINS` 설정값을 로컬 환경변수에서 로드되도록 구성한 점은 훌륭합니다. 향후 DevOps가 인프라를 구성할 때 ECS(Fargate) 환경변수 설정을 안전하게 제어하기 용이해졌습니다.
- Redis client 호출 실패 시의 `Fail-open` 예외 처리(`except redis.RedisError: pass`)는 Rate Limit 구성 요소로 인해 핵심 로메인 로직(검색 및 LLM)이 마비되는 것을 방지합니다. 아주 좋은 설계 패턴(Best Practice)입니다.

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] Critical 항목이 수정되기 전까지 머지를 보류하세요.
