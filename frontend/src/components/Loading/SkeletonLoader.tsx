/**
 * SkeletonLoader.tsx
 * RAG 분석 대기 중 표시되는 스켈레톤 로딩 UI 컴포넌트
 * 단계별 메시지와 프로그레스 바를 표시합니다.
 */

interface SkeletonLoaderProps {
    percent: number;
    message: string;
    onCancel?: () => void;
}

export function SkeletonLoader({ percent, message, onCancel }: SkeletonLoaderProps) {
    return (
        <div className="w-full max-w-4xl mx-auto mt-6 animate-in fade-in duration-300">
            {/* 헤더 스켈레톤 */}
            <div className="bg-gradient-to-br from-slate-900 to-blue-900 rounded-t-2xl p-8 text-white shadow-xl">
                <div className="h-8 w-64 bg-white/20 rounded-lg mb-3 animate-pulse" />
                <div className="h-4 w-48 bg-white/10 rounded animate-pulse" />
            </div>

            {/* 본문 로딩 영역 */}
            <div className="bg-white p-8 rounded-b-2xl shadow-xl border border-gray-100/50">
                {/* 진행 상태 메시지 */}
                <div className="text-center mb-8">
                    <p className="text-blue-600 font-semibold text-lg mb-1 animate-pulse">
                        {message || '분석을 시작합니다...'}
                    </p>
                    <p className="text-gray-400 text-sm">잠시만 기다려 주세요 (최대 60초)</p>
                </div>

                {/* 프로그레스 바 */}
                <div className="mb-8">
                    <div className="flex justify-between text-xs text-gray-500 mb-2">
                        <span>분석 진행률</span>
                        <span className="font-bold text-blue-600">{percent}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                        <div
                            className="h-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${percent}%` }}
                        />
                    </div>
                </div>

                {/* 스켈레톤 카드들 */}
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="p-5 border-2 border-gray-100 rounded-xl animate-pulse">
                            <div className="flex justify-between mb-3">
                                <div className="h-5 w-32 bg-gray-200 rounded" />
                                <div className="h-6 w-20 bg-gray-200 rounded-lg" />
                            </div>
                            <div className="h-4 w-3/4 bg-gray-100 rounded mb-2" />
                            <div className="h-4 w-full bg-gray-100 rounded mb-1" />
                            <div className="h-4 w-2/3 bg-gray-100 rounded" />
                        </div>
                    ))}
                </div>

                {/* 취소 버튼 */}
                {onCancel && (
                    <div className="text-center mt-8">
                        <button
                            onClick={onCancel}
                            className="px-6 py-2 text-gray-400 border border-gray-200 rounded-xl hover:text-gray-600 hover:border-gray-300 transition-all text-sm"
                        >
                            분석 취소
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
