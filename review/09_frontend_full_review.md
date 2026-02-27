### 🔍 총평 (Architecture Review)
전체 파일 재구성이 완료되어 12개 파일이 정상적으로 존재하며 `main.tsx → App.tsx → 컴포넌트 → 훅`의 단방향 데이터 흐름이 잘 설계되어 있습니다. 여러 차례의 리뷰 사이클을 통해 Critical 및 Warning 항목들이 대부분 해소된 점은 긍정적이며, 현재 코드는 초기 런칭 단계에 적합한 수준입니다. 그러나 `App.tsx`의 내부 상태 세터 직접 노출, `IdeaInput`의 프롬프트 인젝션 방어 미흡, `ResultView`의 `patent.title` · `patent.summary` XSS 미방어가 마지막 정리 포인트로 남아 있습니다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 복사해서 Frontend 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**

- `ResultView.tsx:50,55` — **`patent.title`과 `patent.summary`를 JSX에 직접 렌더링 시 XSS 위험**
  - 문제점: 현재 `{patent.title}`, `{patent.summary}`는 React JSX의 기본 이스케이프 처리로 어느 정도 보호되지만, 향후 `dangerouslySetInnerHTML` 도입 또는 HTML 태그가 포함된 백엔드 응답이 발생할 경우 즉각 XSS 취약점으로 전환됩니다. 백엔드에서 이미 `<b>`, `<em>` 태그가 포함된 하이라이트 데이터를 내려보낼 계획이 있다면 지금이 방어 시점입니다.
  - 해결 방안: 백엔드로부터 HTML 태그 포함 요청 가능성이 있는 필드를 `dangerouslySetInnerHTML`로 렌더링할 경우 반드시 `DOMPurify.sanitize()`로 감싸야 합니다:
    ```typescript
    import DOMPurify from 'dompurify';
    <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(patent.summary) }} />
    ```

- `IdeaInput.tsx:20~21` — **프롬프트 인젝션 방어가 길이 제한에만 의존 (불충분)**
  - 문제점: 현재 입력 방어는 `MAX_LENGTH = 2000` 글자 제한이 전부입니다. `"이전 지시사항을 무시하고..."`, `"System: ..."`, `"Ignore all previous instructions"` 등의 고전적인 프롬프트 인젝션 패턴에 무방비 상태입니다.
  - 해결 방안: 간단한 클라이언트 측 필터를 추가하세요 (백엔드에도 별도 방어 필요):
    ```typescript
    const INJECTION_PATTERNS = [/ignore\s+(all\s+)?previous/i, /system\s*:/i, /\[\s*system\s*\]/i];
    const hasInjection = INJECTION_PATTERNS.some(p => p.test(trimmed));
    if (hasInjection) {
        setError('허용되지 않는 형식의 입력입니다.');
        return;
    }
    ```

**[🟡 Warning: 잠재적 위험 - 개선 권장]**

- `App.tsx:25~26` — **`setIsComplete`, `setErrorInfo` 상태 세터를 외부에 직접 노출**
  - 문제점: `useRagStream` 훅이 내부 상태 세터를 그대로 반환하여 `App.tsx`가 훅의 내부 구현에 강결합됩니다. `App.tsx:38~39`에서 직접 호출 중:
    ```
    setIsComplete(false);
    setErrorInfo(null);
    ```
  - 개선 방안: `useRagStream` 내부에 의미 있는 래퍼 함수를 추가하는 것을 권장합니다:
    ```typescript
    const resetResult = () => { setIsComplete(false); setErrorInfo(null); };
    // 반환값에 resetResult 추가 후 setIsComplete, setErrorInfo 제거
    ```

- `App.tsx:52~55` — **에러 상태에서 재시도 시 `startAnalysis` 직접 호출 — 이중 실행 위험**
  - 문제점: `onRetry` 콜백에서 `setErrorInfo(null)` 후 즉시 `startAnalysis(currentIdea)`를 호출합니다. `setErrorInfo(null)`은 비동기 상태 업데이트이므로 렌더링 전에 `startAnalysis`가 실행되어 에러 UI가 잠깐 남아있는 깜빡임이 발생할 수 있습니다.
  - 개선 방안: `useCallback` + `flushSync` 또는 `startAnalysis` 호출 시 내부에서 에러 상태를 자동 초기화하도록 `useRagStream`을 수정하세요.

**[🟢 Info: 클린 코드 및 유지보수 제안]**

- `ResultView.tsx:58~61` — **KIPRIS 링크 플레이스홀더가 사용자에게 노출됨**
  - 현재 `"📌 원문 링크: 백엔드에서 patent.url 필드 제공 시 연결 예정"` 텍스트가 실제 UI에 노출됩니다. 아직 데이터가 없는 경우 해당 영역을 완전히 숨겨야 합니다:
    ```tsx
    {patent.url && <a href={patent.url} target="_blank">원문 보기</a>}
    ```

- `App.tsx:113` — **`isLoading={isAnalyzing}` prop 명칭 혼재**
  - `IdeaInput`의 prop 이름은 `isLoading`인데 `App`에서는 `isAnalyzing` 상태를 전달합니다. 일관된 네이밍을 위해 둘 중 하나로 통일하세요.

---

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] **XSS 방어 강화(`DOMPurify` 준비) 및 프롬프트 인젝션 필터 추가가 선행된 후 머지를 권장합니다.** 현재 기능 동작에는 문제 없으나, 보안 관점에서 프로덕션 배포 전 Critical 2건 처리가 필요합니다.
