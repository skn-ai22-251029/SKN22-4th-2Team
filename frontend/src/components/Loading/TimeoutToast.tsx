import { useEffect, useState } from 'react';

interface TimeoutToastProps {
    isAnalyzing: boolean;
    timeoutMs?: number; // 기본값 30초 (30000ms)
}

export function TimeoutToast({ isAnalyzing, timeoutMs = 30000 }: TimeoutToastProps) {
    const [showToast, setShowToast] = useState(false);

    useEffect(() => {
        let timer: NodeJS.Timeout;

        if (isAnalyzing) {
            // 분석이 시작되면 타이머 가동
            timer = setTimeout(() => {
                setShowToast(true);
            }, timeoutMs);
        } else {
            // 분석이 끝나거나 취소되면 타이머 클리어 및 토스트 숨김
            setShowToast(false);
        }

        return () => {
            if (timer) clearTimeout(timer);
        };
    }, [isAnalyzing, timeoutMs]);

    if (!showToast) return null;

    return (
        <div className="fixed bottom-6 right-6 max-w-sm w-full bg-white border-l-4 border-amber-500 shadow-xl rounded-lg p-5 animate-slide-up z-50">
            <div className="flex items-start">
                <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>
                <div className="ml-3 w-0 flex-1 pt-0.5">
                    <p className="text-sm font-bold text-gray-900">
                        분석이 지연되고 있습니다
                    </p>
                    <p className="mt-1 text-sm text-gray-500 leading-relaxed">
                        현재 특허 DB 검색 및 AI 리포트 생성에 평소보다 오랜 시간이 소요 중입니다.
                        조금만 더 기다려 주시면 정확한 결과를 안내해 드리겠습니다.
                    </p>
                </div>
                <div className="ml-4 flex-shrink-0 flex">
                    <button
                        onClick={() => setShowToast(false)}
                        className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
                    >
                        <span className="sr-only">닫기</span>
                        <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
