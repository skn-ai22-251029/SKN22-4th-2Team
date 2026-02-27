import { useState, useCallback } from 'react';
import { IdeaInput } from './components/Form/IdeaInput';
import { SkeletonLoader } from './components/Loading/SkeletonLoader';
import { ResultView } from './components/Result/ResultView';
import { ErrorFallback } from './components/common/ErrorFallback';
import { RateLimitModal } from './components/common/RateLimitModal';
import { HistorySidebar } from './components/History/HistorySidebar';
import { useRagStream } from './hooks/useRagStream';
import { exportPdf } from './utils/exportPdf';
import { HistoryRecord } from './types/rag';

/**
 * App.tsx
 * Short-Cut 애플리케이션의 최상위 컴포넌트
 * 입력 → 로딩(스켈레튼) → 결과 → 재시도 흐름을 관리합니다.
 * [#25 추가] Rate Limit 전용 오버레이 모달, 검색 히스토리 사이드바 통합
 */
function App() {
    const {
        isAnalyzing,
        isSkeletonVisible,
        isComplete,
        percent,
        message,
        resultData,
        errorInfo,
        startAnalysis,
        cancelAnalysis,
        setIsComplete,
        setErrorInfo,
        setResultData  // [11번 리뷰 반영] Critical: 캐시 결과 직접 주입용
    } = useRagStream();

    const [currentIdea, setCurrentIdea] = useState('');

    // [#25] 히스토리 사이드바 열림/닫힐 상태
    const [isHistoryOpen, setIsHistoryOpen] = useState(false);

    // [11번 리뷰 반영] Critical: 문자열 비교 대신 code 필드로 판별
    const isRateLimited = errorInfo?.code === 'RATE_LIMITED';

    // [11번 리뷰 반영] Info: handleSubmit을 useCallback으로 래핑 (안정적 상태 유지)
    const handleSubmit = useCallback((idea: string) => {
        setCurrentIdea(idea);
        startAnalysis(idea);
    }, [startAnalysis]);

    const handleReset = useCallback(() => {
        setIsComplete(false);
        setErrorInfo(null);
    }, [setIsComplete, setErrorInfo]);

    // [11번 리뷰 반영] Critical: 캐시 결과가 있으면 setResultData로 직접 주입, startAnalysis 호출 제거
    const handleViewHistoryResult = useCallback((record: HistoryRecord) => {
        if (record.result) {
            // 캐시된 결과가 있으면 재요청 없이 직접 주입
            setResultData(record.result);
            setIsComplete(true);
            setErrorInfo(null);
            setIsHistoryOpen(false);
        } else {
            // 결과 캐시 없으면 재분석
            setIsHistoryOpen(false);
            handleSubmit(record.idea);
        }
    }, [setResultData, setIsComplete, setErrorInfo, handleSubmit]);

    // [11번 리뷰 반영] Info: handleSubmit을 의존성에 정상 선언 (안정적 참조)
    const handleRerun = useCallback((idea: string) => {
        handleReset();
        handleSubmit(idea);
    }, [handleReset, handleSubmit]);

    // Rate Limit 에러인지 일반 에러인지 분기
    const isGeneralError = errorInfo && !isRateLimited && !isAnalyzing;

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 py-12">

            {/* ── 글로벌 헤더 ── */}
            <header className="fixed top-0 left-0 right-0 z-20 flex items-center justify-between px-6 py-3 bg-white/80 backdrop-blur-md border-b border-gray-100/80 shadow-sm">
                <span className="text-lg font-black text-slate-900 tracking-tight">✂️ Short-Cut</span>
                <button
                    onClick={() => setIsHistoryOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all"
                >
                    📋 <span className="hidden sm:inline">검색 히스토리</span>
                </button>
            </header>

            {/* ── Rate Limit 전용 오버레이 모달 (#25) ── */}
            {isRateLimited && (
                <RateLimitModal
                    onClose={() => setErrorInfo(null)}
                    onViewHistory={() => {
                        setErrorInfo(null);
                        setIsHistoryOpen(true);
                    }}
                />
            )}

            {/* ── 히스토리 사이드바 (#25) ── */}
            <HistorySidebar
                isOpen={isHistoryOpen}
                onClose={() => setIsHistoryOpen(false)}
                onViewResult={handleViewHistoryResult}
                onRerun={handleRerun}
            />

            {/* ── 메인 콘텐츠 (헤더 높이 만큼 padding-top) ── */}
            <div className="container mx-auto px-4 pt-16">

                {/* 일반 에러 상태 (Rate Limit 제외) */}
                {isGeneralError && (
                    <div className="w-full max-w-4xl mx-auto mt-6 animate-in fade-in duration-300">
                        <ErrorFallback
                            title={errorInfo!.title}
                            message={errorInfo!.message}
                            onRetry={() => {
                                setErrorInfo(null);
                                if (currentIdea) startAnalysis(currentIdea);
                            }}
                        />
                        <div className="text-center mt-4">
                            <button
                                onClick={handleReset}
                                className="text-sm text-gray-400 hover:text-gray-600 underline transition-colors"
                            >
                                새 아이디어로 돌아가기
                            </button>
                        </div>
                    </div>
                )}

                {/* 스켈레톤 로딩 */}
                {isAnalyzing && isSkeletonVisible && (
                    <SkeletonLoader
                        percent={percent}
                        message={message}
                        onCancel={cancelAnalysis}
                    />
                )}

                {/* 분석 진행 중 (스켈레톤 이후 프로그레스) */}
                {isAnalyzing && !isSkeletonVisible && (
                    <div className="w-full max-w-4xl mx-auto mt-6 text-center">
                        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
                            <p className="text-blue-600 font-bold text-lg animate-pulse mb-4">
                                {message}
                            </p>
                            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                                <div
                                    className="h-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500"
                                    style={{ width: `${percent}%` }}
                                />
                            </div>
                            <p className="text-gray-400 text-sm mt-3">{percent}% 완료</p>
                        </div>
                    </div>
                )}

                {/* 결과 화면 */}
                {isComplete && resultData && !isAnalyzing && (
                    <ResultView
                        riskLevel={resultData.riskLevel}
                        riskScore={resultData.riskScore}
                        similarCount={resultData.similarCount}
                        uniqueness={resultData.uniqueness}
                        topPatents={resultData.topPatents}
                        onReset={handleReset}
                        onExportPdf={() => exportPdf('result-view')}
                    />
                )}

                {/* 입력 화면 */}
                {!isAnalyzing && !isComplete && !isGeneralError && !isRateLimited && (
                    <div className="flex flex-col items-center justify-center min-h-[70vh]">
                        <IdeaInput
                            onSubmit={handleSubmit}
                            isLoading={isAnalyzing}
                        />
                    </div>
                )}

            </div>
        </div>
    );
}

export default App;
