import { useEffect, useRef, useState } from 'react'; // [11번 리뷰 반영] Warning: 미사용 useCallback 제거

interface RateLimitModalProps {
    retryAfter?: number; // 서버에서 받은 재시도 대기 시간(초), 없으면 카운트다운 없음
    onClose: () => void;
    onViewHistory: () => void;
}

/**
 * RateLimitModal.tsx
 * 429 Too Many Requests 발생 시 오버레이 형태로 표시되는 전용 안내 모달
 * - 화면 뒤(입력창)를 유지하고 오버레이만 노출
 * - Retry-After 서버 응답 헤더 기반 카운트다운 타이머 지원
 * - 검색 히스토리 사이드바 열기 CTA 버튼 포함
 */
export function RateLimitModal({ retryAfter, onClose, onViewHistory }: RateLimitModalProps) {
    const [remaining, setRemaining] = useState<number | null>(retryAfter ?? null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // 카운트다운 타이머 실행
    // [11번 리뷰 반영] Warning: retryAfter 변경 시 타이머 재시작을 위해 의존성에 선언
    useEffect(() => {
        if (retryAfter && retryAfter > 0) {
            setRemaining(retryAfter);
        }
        if (!remaining || remaining <= 0) return;

        timerRef.current = setInterval(() => {
            setRemaining(prev => {
                if (prev === null || prev <= 1) {
                    clearInterval(timerRef.current!);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [retryAfter]); // retryAfter 변경 시 타이머 재초기화

    // 남은 시간 포맷팅 (초 → 시:분:초)
    const formatTime = (secs: number): string => {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;
        if (h > 0) return `${h}시간 ${m}분`;
        if (m > 0) return `${m}분 ${s}초`;
        return `${s}초`;
    };

    return (
        // 오버레이 배경 — 클릭 시 닫기
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="w-full max-w-md mx-4 bg-white rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                {/* 헤더 */}
                <div className="bg-gradient-to-br from-orange-500 to-red-500 p-8 text-white text-center">
                    <div className="text-5xl mb-3">🚦</div>
                    <h2 className="text-2xl font-black">분석 한도에 도달했습니다</h2>
                    <p className="text-white/80 text-sm mt-2">오늘의 분석 횟수를 모두 사용하셨습니다</p>
                </div>

                {/* 본문 */}
                <div className="p-8 text-center">
                    {/* 카운트다운 타이머 */}
                    {remaining !== null && remaining > 0 && (
                        <div className="mb-6 p-4 bg-orange-50 rounded-2xl border border-orange-100">
                            <p className="text-orange-600 text-xs font-bold uppercase tracking-wide mb-1">
                                ⏰ 다음 분석까지
                            </p>
                            <p className="text-3xl font-black text-orange-700">
                                {formatTime(remaining)}
                            </p>
                        </div>
                    )}
                    {remaining === 0 && (
                        <div className="mb-6 p-4 bg-green-50 rounded-2xl border border-green-100">
                            <p className="text-green-600 font-bold">✅ 이제 다시 시도할 수 있습니다!</p>
                        </div>
                    )}
                    {remaining === null && (
                        <p className="text-gray-500 text-sm mb-6 leading-relaxed">
                            잠시 후 다시 시도하거나,<br />
                            과거 분석 내역을 확인해 보세요.
                        </p>
                    )}

                    {/* CTA 버튼 */}
                    <div className="flex flex-col gap-3">
                        <button
                            onClick={onViewHistory}
                            className="w-full py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-700 transition-all"
                        >
                            📋 검색 히스토리 보기
                        </button>
                        <button
                            onClick={onClose}
                            className="w-full py-3 text-gray-400 border border-gray-200 rounded-xl hover:text-gray-600 hover:border-gray-300 transition-all text-sm"
                        >
                            닫기
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
