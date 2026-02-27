import { ReactNode } from 'react';

interface ErrorFallbackProps {
    title: string;
    message: string;
    onRetry: () => void;
}

export function ErrorFallback({ title, message, onRetry }: ErrorFallbackProps) {
    return (
        <div className="w-full max-w-2xl mx-auto mt-10 p-8 bg-white rounded-2xl shadow-lg border border-red-100 flex flex-col items-center text-center animate-in fade-in slide-in-from-bottom-5">
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-6">
                <span className="text-3xl">⚠️</span>
            </div>

            <h2 className="text-2xl font-bold text-gray-800 mb-3">
                {title}
            </h2>

            <div className="bg-gray-50 p-4 rounded-lg w-full mb-8 border border-gray-100">
                <p className="text-gray-600 font-medium">
                    {message}
                </p>
                {title.includes('텍스트가 너무 깁니다') && (
                    <p className="text-sm text-gray-500 mt-2">
                        💡 조치사항: 핵심 아이디어만 간결하게 다시 입력해 주세요. (500자 이내 권장)
                    </p>
                )}
                {title.includes('결과를 찾지 못했습니다') && (
                    <p className="text-sm text-gray-500 mt-2">
                        💡 대안: 다른 키워드 또는 더 포괄적인 단어로 다시 시도해 보세요.
                    </p>
                )}
            </div>

            <button
                onClick={onRetry}
                className="px-8 py-3 bg-gray-900 hover:bg-gray-800 text-white font-bold rounded-xl transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 flex items-center gap-2"
            >
                <span>다시 아이디어 입력하기</span>
                <span>🔄</span>
            </button>
        </div>
    );
}
