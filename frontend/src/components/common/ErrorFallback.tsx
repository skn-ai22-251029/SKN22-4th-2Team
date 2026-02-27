interface ErrorFallbackProps {
    title: string;
    message: string;
    onRetry?: () => void;
}

/**
 * 에러 발생 시 사용자에게 표시하는 Fallback UI 컴포넌트
 * 에러 유형별 친화적 메시지와 복구 경로(재시도 버튼)를 제공합니다.
 */
export function ErrorFallback({ title, message, onRetry }: ErrorFallbackProps) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 p-6">
            <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center border border-gray-100">
                {/* 에러 아이콘 */}
                <div className="text-6xl mb-4">⚠️</div>

                {/* 에러 제목 */}
                <h2 className="text-xl font-bold text-gray-800 mb-3">{title}</h2>

                {/* 에러 메시지 */}
                <p className="text-gray-500 text-sm leading-relaxed mb-6">{message}</p>

                {/* 재시도 버튼 */}
                {onRetry && (
                    <button
                        onClick={onRetry}
                        className="px-6 py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-700 transition-all shadow-md"
                    >
                        🔄 다시 시도
                    </button>
                )}
            </div>
        </div>
    );
}
