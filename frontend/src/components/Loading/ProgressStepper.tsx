import { useState, useEffect } from 'react';

interface ProgressStepperProps {
    percent: number;
    message: string;
    onCancel?: () => void;
}

export function ProgressStepper({ percent, message, onCancel }: ProgressStepperProps) {
    const [elapsedSeconds, setElapsedSeconds] = useState(0);

    // 30초 로딩 타이머
    useEffect(() => {
        const timer = setInterval(() => {
            setElapsedSeconds(prev => prev + 1);
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    // 단계별 텍스트 및 활성화 상태 매핑
    const currentStep = percent < 40 ? 1 : percent < 70 ? 2 : 3;

    return (
        <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-xl shadow-md border border-gray-100 mb-6">

            {/* 알림 토스트 (30초 초과) */}
            {elapsedSeconds > 30 && (
                <div className="mb-4 p-3 bg-amber-50 text-amber-800 rounded-md text-sm flex items-center">
                    <span className="mr-2">⏱️</span>
                    평소보다 분석 시간이 오래 걸리고 있습니다. 조금만 더 대기해 주세요.
                </div>
            )}

            {/* 헤더 영역 (취소 버튼 포함) */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h3 className="text-lg font-bold text-gray-800">특허 분석 진행 중...</h3>
                    <p className="text-sm text-gray-500 mt-1">예상 소요 시간: 약 30초 ✨</p>
                </div>
                {onCancel && (
                    <button
                        onClick={onCancel}
                        className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-md transition-colors"
                    >
                        정지 (Stop)
                    </button>
                )}
            </div>

            {/* 진행 바 */}
            <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-in-out"
                    style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
                ></div>
            </div>
            <p className="text-right text-xs text-gray-500 font-mono mb-8">{percent}%</p>

            {/* 단계별 스텝퍼 아이콘 및 텍스트 */}
            <div className="flex justify-between relative">
                <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -z-10 -translate-y-1/2"></div>

                {/* Step 1 */}
                <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${currentStep >= 1 ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-500'}`}>
                        🔍
                    </div>
                    <span className={`text-xs mt-2 font-medium ${currentStep >= 1 ? 'text-blue-700' : 'text-gray-400'}`}>관련 특허 검색</span>
                </div>

                {/* Step 2 */}
                <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${currentStep >= 2 ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-500'}`}>
                        📊
                    </div>
                    <span className={`text-xs mt-2 font-medium ${currentStep >= 2 ? 'text-blue-700' : 'text-gray-400'}`}>유사도 분석</span>
                </div>

                {/* Step 3 */}
                <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${currentStep >= 3 ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-500'}`}>
                        📝
                    </div>
                    <span className={`text-xs mt-2 font-medium ${currentStep >= 3 ? 'text-blue-700' : 'text-gray-400'}`}>보고서 생성</span>
                </div>
            </div>

            {/* 현재 상태 상세 메시지 */}
            <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-700 text-center animate-pulse">{message || '시스템을 준비하고 있습니다...'}</p>
            </div>

        </div>
    );
}
