/**
 * exportPdf.ts
 * 분석 결과를 PDF로 내보내는 유틸리티 함수
 * html2canvas + jsPDF 없이 브라우저 기본 print 기능을 활용합니다.
 */

/**
 * 지정된 HTML 요소를 브라우저 인쇄 다이얼로그를 이용해 PDF로 저장
 * @param elementId - PDF로 내보낼 HTML 요소의 ID
 * @param delayMs - 렌더링 대기 시간 (ms), 기본 300ms
 */
export const exportPdf = (elementId = 'result-view', delayMs = 300): void => {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`exportPdf: #${elementId} 요소를 찾을 수 없습니다.`);
        return;
    }

    // 인쇄 전 대기 (스타일 렌더링 완료 보장)
    setTimeout(() => {
        window.print();
    }, delayMs);
};
