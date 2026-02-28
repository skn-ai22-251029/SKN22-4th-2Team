import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

/**
 * 특정 HTML 요소(ref)를 고화질 캡쳐하여 PDF로 다운로드하는 유틸리티
 * @param elementRef 캡처할 대상의 React RefObject
 * @param filename 저장할 파일명 (단, 확장자 .pdf는 내부에서 추가됨)
 */
export const downloadPdfFromElement = async (
    elementRef: React.RefObject<HTMLElement>,
    filename: string = 'Shortcut_Patent_Report'
) => {
    if (!elementRef.current) {
        console.error("PDF 변환을 위한 DOM 요소를 찾을 수 없습니다.");
        return false;
    }

    try {
        // 1. html2canvas 옵션: 해상도(scale), CSS 로딩(useCORS) 등 최적화
        const canvas = await html2canvas(elementRef.current, {
            scale: 2,           // 레티나 디스플레이 등 화질 열화 방지를 위한 2배율 캡처
            useCORS: true,      // 외부 이미지(웹 아이콘 등) 렌더링 허용
            backgroundColor: '#ffffff' // 투명한 배경일 경우 흰색으로 처리
        });

        // 2. 캡처된 캔버스를 이미지 URL(PNG)로 변환
        const imgData = canvas.toDataURL('image/png');

        // 3. A4 규격(210x297mm) 단위 설정
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

        // 만약 컨텐츠 길이가 A4 1장을 넘어간다면 여러 장으로 잘라내는게 정석이나,
        // 현재는 요약 리포트 수준(1장 내외)이므로 단일 페이지 상단부터 축소/확대 배치
        pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, Math.min(pdfHeight, pdf.internal.pageSize.getHeight()));

        // 4. 클라이언트 브라우저에서 다운로드 발생
        pdf.save(`${filename}.pdf`);
        return true;
    } catch (error) {
        console.error("PDF 생성 중 오류가 발생했습니다:", error);
        return false;
    }
};
