### 🔍 총평 (Architecture Review)
`ResultView`의 카드 분리(`PatentCard` 컴포넌트 독립)와 상태 기반 컬러 코딩 시스템은 13번 기획 의도를 충실히 구현했으며, 아키텍처 관점에서 단일 책임 원칙(SRP)을 잘 지킨 코드입니다. 다만 KIPRIS 링크가 모든 카드에 동일한 하드코딩 URL을 가리키는 보안/UX 허점과, `dangerouslySetInnerHTML` 향후 사용에 대한 XSS 방어 미비가 반드시 수정 전 대비되어야 합니다.

---

### 🚨 코드 리뷰 피드백 (개발 에이전트 전달용)
*(아래 내용을 Frontend 에이전트에게 전달하세요)*

**[🔴 Critical: 치명적 결함 - 즉시 수정 필요]**
- `ResultView.tsx:33` - **KIPRIS 원문 URL 전체 하드코딩 (모든 카드가 동일 페이지로 이동)**
  - 문제점: 현재 모든 특허 카드가 `http://kpat.kipris.or.kr/kpat/searchLogina.do?next=MainSearch#page1` 고정 URL을 가리킵니다. 사용자가 "원문 조회"를 눌러도 특정 특허가 아닌 KIPRIS 검색 홈으로 이동하여 UX를 크게 헤칩니다.
  - 해결 방안: 백엔드 API 응답에 `patent.url` 또는 `patent.applicationNumber` 필드를 추가해달라고 협력 요청한 뒤, `href={patent.url ?? 'https://www.kipris.or.kr'}` 형태로 동적 연결하거나, 번호 기반 KIPRIS 검색 쿼리 URL(`https://www.kipris.or.kr/khome/search.do?query=${patent.id}`)을 임시 대안으로 활용하세요.

- `ResultView.tsx:54` - **`dangerouslySetInnerHTML` 사전 XSS 방어 없이 향후 사용 예약**
  - 문제점: 코드 주석에 "향후 백엔드 데이터에 강조태그 포함 시 `dangerouslySetInnerHTML` 대응 가능"이라고 명시되어 있지만, 이를 그냥 적용하면 악성 스크립트 삽입(XSS) 위험이 매우 높습니다. 백엔드에서 `<script>` 또는 `<img onerror="">` 류의 페이로드가 하이라이트 필드에 담겨 올 경우, 브라우저에서 그대로 실행될 수 있습니다.
  - 해결 코드 제안: 반드시 `DOMPurify.sanitize(patent.highlightedSummary)` 결과물만 `dangerouslySetInnerHTML`에 주입하세요. `DOMPurify` 패키지를 `package.json`에 추가 의존성으로 반영하는 것을 적극 권장합니다.

**[🟡 Warning: 잠재적 위험 - 개선 권장]**
- `ResultView.tsx:77` - **`getRiskStyles`의 파라미터 타입이 `string`으로 느슨함**
  - 문제점: `riskLevel` 값이 `'High' | 'Medium' | 'Low'`로 명확하게 정의되어 있음에도 불구하고, `getRiskStyles(level: string)` 으로 받고 있습니다. 잘못된 값이 들어왔을 때 `default` 스타일로 조용히 fallback됩니다.
  - 개선 방안: `getRiskStyles(level: RagAnalysisResult['riskLevel'])` 처럼 타입을 리터럴 유니언으로 좁혀두면 컴파일 타임에 오타를 잡을 수 있습니다.

- `ResultView.tsx:66` - **`setTimeout` 내부 `async/await`에서 에러 미처리**
  - 문제점: `setTimeout` 내의 `async` 콜백이 `downloadPdfFromElement` 실패 시 `success === false`로만 처리하지만, 함수 자체가 `throw`를 할 경우 `try-catch`가 없어 Silent Error가 됩니다.
  - 개선 방안: `setTimeout(async () => { try { ... } catch(e) { setIsExporting(false); alert('PDF 오류'); } }, 300)` 패턴으로 감싸세요.

**[🟢 Info: 클린 코드 및 유지보수 제안]**
- `ResultView.tsx:135` - **`key={idx}` 배열 인덱스를 React key로 사용**
  - 조언: 배열이 동적으로 재정렬되거나 항목이 삭제될 경우 오작동 가능성이 있습니다. `patent.id` 값이 고유하다면 `key={patent.id}`가 훨씬 안전합니다.
- `ResultView.tsx:104` - **아이디어 출력 시 `"` 하드코딩 배치**
  - 조언: `"{idea}"` 방식은 아이디어 내용에 큰따옴표(`"`)가 포함되면 중첩되어 혼란을 줄 수 있습니다. `&ldquo;{idea}&rdquo;` 또는 CSS 스타일로 처리하는 방법을 권장합니다.

---

### 💡 Tech Lead의 머지(Merge) 권고
- [ ] 이대로 Main 브랜치에 머지해도 좋습니다.
- [x] Critical 항목(KIPRIS URL 하드코딩, XSS 방어 준비 누락)이 수정되기 전까지 머지를 보류하세요.
