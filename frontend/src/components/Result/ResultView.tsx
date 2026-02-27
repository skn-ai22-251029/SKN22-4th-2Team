import { useRef, useState } from 'react';
import { downloadPdfFromElement } from '../../utils/exportPdf';
import { RagAnalysisResult } from '../../types/rag';

interface ResultViewProps {
    idea: string;
    resultData: RagAnalysisResult;
    onReset: () => void;
}

export function ResultView({ idea, resultData, onReset }: ResultViewProps) {
    // HTML 요소를 캡쳐하기 위한 Ref 연결
    const reportRef = useRef<HTMLDivElement>(null);
    const [isExporting, setIsExporting] = useState(false);

    const handleDownloadPdf = async () => {
        setIsExporting(true);
        // 상태 변경으로 렌더링(버튼 숨김 등)이 DOM에 반영될 시간을 살짝 확보
        setTimeout(async () => {
            const success = await downloadPdfFromElement(reportRef, 'Shortcut_Patent_Report');
            setIsExporting(false);
            if (success) {
                alert("리포트가 성공적으로 다운로드되었습니다.");
            } else {
                alert("PDF 생성 중 오류가 발생했습니다.");
            }
        }, 150);
    };

    const getRiskColor = (level: string) => {
        switch (level) {
            case 'High': return 'text-red-600';
            case 'Medium': return 'text-amber-500';
            case 'Low': return 'text-green-600';
            default: return 'text-gray-600';
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto mt-8 animate-fade-in" ref={reportRef}>
            {/* 1. 요약 리포트 헤더 */}
            <div className="bg-gradient-to-r from-blue-700 to-blue-900 rounded-t-xl p-8 text-white shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-white opacity-10 rounded-full blur-2xl"></div>
                <h2 className="text-3xl font-extrabold mb-2 text-white">분석 리포트: 침해 위험도 진단</h2>
                <p className="text-blue-100 font-medium">입력하신 아이디어에 대한 AI RAG 특허 DB 탐색 결과입니다.</p>
            </div>

            {/* 2. 본문 결과 영역 (카드 레이아웃) */}
            <div className="bg-white p-8 rounded-b-xl shadow-lg border border-gray-100">

                {/* 원본 아이디어 리마인드 */}
                <div className="mb-8">
                    <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">분석 대상 아이디어</h3>
                    <div className="p-4 bg-gray-50 border-l-4 border-blue-500 rounded-r-lg text-gray-800 font-medium whitespace-pre-wrap">
                        "{idea}"
                    </div>
                </div>

                {/* 대시보드 요약 (API 데이터 바인딩) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="p-6 bg-red-50 rounded-xl border border-red-100 text-center">
                        <h4 className="text-red-800 font-bold mb-1">침해 위험도</h4>
                        <span className={`text-3xl font-black ${getRiskColor(resultData.riskLevel)}`}>
                            {resultData.riskLevel} ({resultData.riskScore}%)
                        </span>
                    </div>
                    <div className="p-6 bg-blue-50 rounded-xl border border-blue-100 text-center">
                        <h4 className="text-blue-800 font-bold mb-1">유사 특허 발견</h4>
                        <span className="text-3xl font-black text-blue-600">{resultData.similarCount}건</span>
                    </div>
                    <div className="p-6 bg-green-50 rounded-xl border border-green-100 text-center">
                        <h4 className="text-green-800 font-bold mb-1">핵심 차별성</h4>
                        <span className="text-3xl font-black text-green-600">{resultData.uniqueness}</span>
                    </div>
                </div>

                {/* 상세 분석 내용 (Top Patents 매핑) */}
                <div className="mb-10">
                    <h3 className="text-lg font-bold text-gray-800 border-b pb-2 mb-4">🔍 발견된 핵심 유사 특허 요약 (Top {resultData.topPatents.length})</h3>
                    {resultData.topPatents.length > 0 ? (
                        <ul className="space-y-4">
                            {resultData.topPatents.map((patent, idx) => (
                                <li key={idx} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow">
                                    <div className="flex justify-between items-start mb-2">
                                        <span className="font-bold text-blue-700">{patent.id}</span>
                                        <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-bold rounded">
                                            유사도 {patent.similarity}%
                                        </span>
                                    </div>
                                    <h4 className="font-semibold text-gray-800 mb-1">{patent.title}</h4>
                                    <p className="text-gray-600 text-sm">{patent.summary}</p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div className="p-8 text-center text-gray-500 border border-gray-200 rounded-lg">
                            유사한 특허가 발견되지 않았습니다. 혁신적인 아이디어입니다!
                        </div>
                    )}
                </div>

                {/* 액션 버튼 그룹 (캡쳐가 진행될 땐 일시적으로 사라지도록 설정) */}
                {!isExporting && (
                    <div className="flex justify-center flex-col sm:flex-row gap-4 pt-6 border-t border-gray-100" data-html2canvas-ignore="true">
                        <button
                            onClick={handleDownloadPdf}
                            className="px-6 py-3 bg-white border-2 border-gray-200 text-gray-700 font-bold rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-colors flex justify-center items-center"
                        >
                            📥 PDF 리포트 다운로드
                        </button>
                        <button
                            onClick={onReset}
                            className="px-6 py-3 bg-blue-600 text-white font-bold rounded-lg shadow-md hover:bg-blue-700 hover:shadow-lg transition-all flex justify-center items-center"
                        >
                            새로운 아이디어로 검사하기 🔄
                        </button>
                    </div>
                )}

                {/* 캡쳐 진행 중일 때 대체 플레이스홀더 */}
                {isExporting && (
                    <div className="flex justify-center pt-6 border-t border-gray-100 mt-4">
                        <p className="text-sm text-gray-400 font-bold tracking-widest uppercase">END OF REPORT</p>
                    </div>
                )}
            </div>
        </div>
    );
}
