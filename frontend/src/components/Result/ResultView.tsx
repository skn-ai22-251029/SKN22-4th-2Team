import { useRef, useState } from 'react';
import { downloadPdfFromElement } from '../../utils/exportPdf';
import { PatentContext, RagAnalysisResult } from '../../types/rag';

interface ResultViewProps {
    idea: string;
    resultData: RagAnalysisResult;
    onReset: () => void;
}

// 선행 특허 개별 카드 컴포넌트 (PatentContext 기반 타입 적용)
function PatentCard({ patent }: { patent: PatentContext }) {
    // 80% 이상: 위험,  50~79%: 경계, 49% 이하: 안전
    const getSimColor = (sim: number) => {
        if (sim >= 80) return 'bg-red-100 text-red-800 border-red-200';
        if (sim >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
        return 'bg-green-100 text-green-800 border-green-200';
    };

    const getSimBadgeText = (sim: number) => {
        if (sim >= 80) return `🔴 매우 유사 (${sim}%)`;
        if (sim >= 50) return `🟡 부분 유사 (${sim}%)`;
        return `🟢 충돌 낮음 (${sim}%)`;
    };

    return (
        <li className="break-inside-avoid mb-6 p-6 border-2 border-gray-100 rounded-xl hover:shadow-lg hover:border-blue-100 transition-all bg-white relative">
            <div className="flex flex-col sm:flex-row justify-between items-start mb-4 gap-3">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                        <span className="font-extrabold text-blue-900 text-lg">{patent.id}</span>
                        <a
                            href={`http://kpat.kipris.or.kr/kpat/searchLogina.do?next=MainSearch#page1`} // 임시 KIPRIS 연동 URL
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 font-bold transition-colors shadow-sm flex items-center gap-1"
                            title="새 창에서 KIPRIS 특허 원문 보기"
                        >
                            <span>🔗</span> 원문 조회
                        </a>
                    </div>
                    <h4 className="font-bold text-gray-800 text-base leading-snug">{patent.title}</h4>
                </div>

                <div className={`px-3 py-1.5 flex-shrink-0 text-sm font-black rounded-lg border shadow-sm ${getSimColor(patent.similarity)}`}>
                    {getSimBadgeText(patent.similarity)}
                </div>
            </div>

            <div className="bg-gray-50 border border-gray-100 rounded-lg p-4">
                <p className="text-gray-600 text-sm leading-relaxed">
                    {patent.summary}
                </p>
                {/* 13번 기획안 하이라이트 반영 영역 (향후 백엔드 데이터에 강조태그 포함 시 dangerouslySetInnerHTML 대응 가능) */}
            </div>
        </li>
    );
}

export function ResultView({ idea, resultData, onReset }: ResultViewProps) {
    const reportRef = useRef<HTMLDivElement>(null);
    const [isExporting, setIsExporting] = useState(false);

    const handleDownloadPdf = async () => {
        setIsExporting(true);
        setTimeout(async () => {
            const success = await downloadPdfFromElement(reportRef, 'Shortcut_Patent_Report');
            setIsExporting(false);
            if (success) {
                alert("리포트가 성공적으로 다운로드되었습니다.");
            } else {
                alert("PDF 생성 중 오류가 발생했습니다.");
            }
        }, 300); // UI 렌더링 시간을 충분히 확보 (150 -> 300 늘림)
    };

    const getRiskStyles = (level: string) => {
        // High -> Red 기반 위협, Medium -> Yellow 주의, Low -> Green 안전
        switch (level) {
            case 'High': return { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' };
            case 'Medium': return { text: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200' };
            case 'Low': return { text: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200' };
            default: return { text: 'text-gray-700', bg: 'bg-gray-50', border: 'border-gray-200' };
        }
    };
    const riskStyles = getRiskStyles(resultData.riskLevel);

    return (
        <div className="w-full max-w-4xl mx-auto mt-6 animate-in fade-in slide-in-from-bottom-8 duration-500" ref={reportRef}>
            {/* 1. 요약 리포트 헤더 */}
            <div className="bg-gradient-to-br from-slate-900 to-blue-900 rounded-t-2xl p-8 text-white shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-white opacity-10 rounded-full blur-3xl mix-blend-overlay"></div>
                <h2 className="text-3xl font-black mb-2 tracking-tight text-white drop-shadow-md">침해 위험도 분석 리포트</h2>
                <p className="text-blue-200 font-medium">인공지능 RAG 파이프라인 기반 특허 선행 기술 조사 결과</p>
            </div>

            {/* 2. 본문 결과 영역 */}
            <div className="bg-white p-6 sm:p-10 rounded-b-2xl shadow-xl border border-gray-100/50">

                {/* 입력 아이디어 리마인드 */}
                <div className="mb-10">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 pl-1">분석 대상 아이디어</h3>
                    <div className="p-5 bg-slate-50 border-l-4 border-slate-700 rounded-r-xl text-slate-700 font-medium whitespace-pre-wrap leading-relaxed">
                        "{idea}"
                    </div>
                </div>

                {/* 대시보드 요약 (상태별 컬러 바인딩) */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-12">
                    <div className={`p-6 rounded-2xl border-2 text-center transition-all shadow-sm ${riskStyles.bg} ${riskStyles.border}`}>
                        <h4 className="text-gray-600 font-bold mb-2 text-sm uppercase tracking-wider">종합 침해 위험도</h4>
                        <span className={`text-4xl font-black ${riskStyles.text} drop-shadow-sm`}>
                            {resultData.riskLevel} <span className="text-2xl">({resultData.riskScore}%)</span>
                        </span>
                    </div>
                    <div className="p-6 bg-blue-50/50 rounded-2xl border-2 border-blue-100 text-center shadow-sm">
                        <h4 className="text-gray-600 font-bold mb-2 text-sm uppercase tracking-wider">검토된 선행 특허</h4>
                        <span className="text-4xl font-black text-blue-700 drop-shadow-sm">{resultData.similarCount}건</span>
                    </div>
                    <div className="p-6 bg-slate-50 rounded-2xl border-2 border-slate-100 text-center shadow-sm">
                        <h4 className="text-gray-600 font-bold mb-2 text-sm uppercase tracking-wider">핵심 차별성</h4>
                        <span className="text-base font-bold text-slate-700 mt-1 block break-keep leading-tight">{resultData.uniqueness}</span>
                    </div>
                </div>

                {/* 상세 분석 내용 (Card Component 매핑) */}
                <div className="mb-10">
                    <div className="flex items-center justify-between border-b-2 border-gray-100 pb-3 mb-6">
                        <h3 className="text-xl font-bold text-gray-800">🔍 핵심 유사 특허 분석 <span className="text-blue-500 font-black">Top {resultData.topPatents.length}</span></h3>
                    </div>

                    {resultData.topPatents.length > 0 ? (
                        <ul className="space-y-0">
                            {resultData.topPatents.map((patent, idx) => (
                                <PatentCard key={idx} patent={patent} />
                            ))}
                        </ul>
                    ) : (
                        <div className="py-12 px-6 text-center bg-gray-50 border-2 border-dashed border-gray-200 rounded-2xl">
                            <span className="text-4xl mb-4 block">🎉</span>
                            <h4 className="text-lg font-bold text-gray-700 mb-2">유사한 특허가 발견되지 않았습니다.</h4>
                            <p className="text-gray-500">독창적인 아이디어입니다! 곧바로 특허 출원 절차를 밟으시는 것을 추천합니다.</p>
                        </div>
                    )}
                </div>

                {/* 액션 버튼 그룹 (캡쳐가 진행될 땐 숨김) */}
                {!isExporting && (
                    <div className="flex justify-center flex-col sm:flex-row gap-4 pt-8 border-t-2 border-gray-100" data-html2canvas-ignore="true">
                        <button
                            onClick={handleDownloadPdf}
                            className="px-8 py-4 bg-white border-2 border-gray-200 text-gray-700 font-bold rounded-xl hover:bg-gray-50 hover:border-blue-300 hover:text-blue-700 transition-all flex justify-center items-center shadow-sm"
                        >
                            <span className="mr-2 text-xl">📥</span> PDF 리포트 파일로 보관
                        </button>
                        <button
                            onClick={onReset}
                            className="px-8 py-4 bg-slate-900 border-2 border-slate-900 text-white font-bold rounded-xl shadow-md hover:bg-slate-800 hover:shadow-xl hover:-translate-y-0.5 transition-all flex justify-center items-center"
                        >
                            다른 참신한 아이디어 검사하기 <span className="ml-2">🔄</span>
                        </button>
                    </div>
                )}

                {/* 캡쳐 진행 중일 때 문서 끝 표시기 */}
                {isExporting && (
                    <div className="flex justify-center pt-8 mt-4 opacity-50">
                        <p className="text-xs text-gray-400 font-bold tracking-[0.2em] uppercase">- DOCUMENT END -</p>
                    </div>
                )}
            </div>
        </div>
    );
}
