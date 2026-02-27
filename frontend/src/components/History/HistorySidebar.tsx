import { HistoryRecord } from '../../types/rag';
import { useHistory } from '../../hooks/useHistory';
import { HistoryItem, HistoryEmpty } from './HistoryItems';

interface HistorySidebarProps {
    isOpen: boolean;
    onClose: () => void;
    onViewResult: (record: HistoryRecord) => void;
    onRerun: (idea: string) => void;
}

/**
 * HistorySidebar.tsx
 * 검색 히스토리 사이드바 컨테이너
 * - 화면 우측에서 슬라이드인/아웃
 * - 세션 기반 분석 내역 목록 표시
 * - 결과 보기 (캐시 데이터 재활용) / 재분석 버튼
 */
export function HistorySidebar({ isOpen, onClose, onViewResult, onRerun }: HistorySidebarProps) {
    const { records, isLoading, refresh } = useHistory();

    return (
        <>
            {/* 오버레이 배경 (모바일 대응) */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-30 bg-black/30 md:hidden"
                    onClick={onClose}
                />
            )}

            {/* 사이드바 패널 */}
            <aside
                className={`
                    fixed top-0 right-0 z-40 h-full w-80 bg-white shadow-2xl
                    flex flex-col
                    transform transition-transform duration-300 ease-out
                    ${isOpen ? 'translate-x-0' : 'translate-x-full'}
                `}
            >
                {/* 헤더 */}
                <div className="flex items-center justify-between p-5 border-b border-gray-100 shrink-0">
                    <div>
                        <h2 className="text-lg font-black text-gray-800">📋 검색 히스토리</h2>
                        {records.length > 0 && (
                            <p className="text-xs text-gray-400 mt-0.5">총 {records.length}건의 분석 기록</p>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {/* 새로고침 */}
                        <button
                            onClick={refresh}
                            title="새로고침"
                            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-all"
                        >
                            🔄
                        </button>
                        {/* 닫기 */}
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-gray-700 rounded-lg hover:bg-gray-100 transition-all text-xl leading-none"
                        >
                            ✕
                        </button>
                    </div>
                </div>

                {/* 콘텐츠 영역 */}
                <div className="flex-1 overflow-y-auto p-4">
                    {isLoading ? (
                        /* 로딩 스켈레톤 */
                        <div className="space-y-3">
                            {[1, 2, 3].map((i) => (
                                <div key={i} className="p-4 border border-gray-100 rounded-xl animate-pulse">
                                    <div className="flex justify-between mb-2">
                                        <div className="h-5 w-16 bg-gray-200 rounded-full" />
                                        <div className="h-4 w-24 bg-gray-100 rounded" />
                                    </div>
                                    <div className="h-4 w-full bg-gray-100 rounded mb-1" />
                                    <div className="h-4 w-3/4 bg-gray-100 rounded mb-3" />
                                    <div className="flex gap-2">
                                        <div className="h-7 flex-1 bg-gray-200 rounded-lg" />
                                        <div className="h-7 flex-1 bg-gray-100 rounded-lg" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : records.length === 0 ? (
                        /* 빈 상태 */
                        <HistoryEmpty onGoToInput={onClose} />
                    ) : (
                        /* 히스토리 목록 */
                        <div className="space-y-3">
                            {records.map((record) => (
                                <HistoryItem
                                    key={record.id}
                                    record={record}
                                    onView={onViewResult}
                                    onRerun={(idea) => {
                                        onRerun(idea);
                                        onClose();
                                    }}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* 푸터 안내 */}
                <div className="p-4 border-t border-gray-50 shrink-0">
                    <p className="text-xs text-gray-300 text-center leading-relaxed">
                        현재 세션의 분석 기록만 표시됩니다.
                        <br />
                        시크릿 모드에서는 기록이 저장되지 않습니다.
                    </p>
                </div>
            </aside>
        </>
    );
}
