import { HistoryRecord } from '../../types/rag';

interface HistoryEmptyProps {
    onGoToInput: () => void;
}

/**
 * HistoryEmpty.tsx
 * 히스토리 기록이 없을 때 표시되는 빈 상태 플레이스홀더
 */
export function HistoryEmpty({ onGoToInput }: HistoryEmptyProps) {
    return (
        <div className="flex flex-col items-center justify-center h-full py-16 px-6 text-center">
            <div className="text-6xl mb-6 opacity-50">📭</div>
            <h3 className="text-base font-bold text-gray-500 mb-2">아직 분석 기록이 없습니다</h3>
            <p className="text-sm text-gray-400 leading-relaxed mb-6">
                첫 번째 특허 검증을<br />시작해 보세요!
            </p>
            <button
                onClick={onGoToInput}
                className="px-6 py-2.5 bg-slate-900 text-white text-sm font-bold rounded-xl hover:bg-slate-700 transition-all"
            >
                ✏️ 아이디어 입력하기
            </button>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
// HistoryItem: 개별 히스토리 카드
// ─────────────────────────────────────────────────────────────

const RISK_BADGE = {
    High: { label: '높음', className: 'bg-red-100 text-red-700 border-red-200', icon: '🔴' },
    Medium: { label: '중간', className: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: '🟡' },
    Low: { label: '낮음', className: 'bg-green-100 text-green-700 border-green-200', icon: '🟢' },
} as const;

interface HistoryItemProps {
    record: HistoryRecord;
    onView: (record: HistoryRecord) => void;
    onRerun: (idea: string) => void;
}

/**
 * HistoryItem.tsx
 * 개별 검색 히스토리 카드 컴포넌트
 * 위험도 뱃지, 아이디어 요약, 분석 일시, 결과 보기/재분석 버튼 포함
 */
export function HistoryItem({ record, onView, onRerun }: HistoryItemProps) {
    const badge = RISK_BADGE[record.riskLevel];

    // 날짜 포맷팅
    const formattedDate = new Date(record.createdAt).toLocaleString('ko-KR', {
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    // 아이디어 50자 truncate
    const ideaPreview = record.idea.length > 50
        ? record.idea.slice(0, 50) + '...'
        : record.idea;

    return (
        <div className="p-4 border border-gray-100 rounded-xl hover:border-blue-100 hover:shadow-sm transition-all bg-white">
            {/* 헤더: 뱃지 + 날짜 */}
            <div className="flex items-center justify-between mb-2">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${badge.className}`}>
                    {badge.icon} {badge.label}
                </span>
                <span className="text-xs text-gray-400">{formattedDate}</span>
            </div>

            {/* 아이디어 요약 */}
            <p className="text-sm text-gray-700 font-medium leading-relaxed mb-2 line-clamp-2">
                {ideaPreview}
            </p>

            {/* 유사 특허 수 */}
            <p className="text-xs text-gray-400 mb-3">
                📄 유사 특허 {record.similarCount}건 · {record.riskScore}% 위험도
            </p>

            {/* 액션 버튼 */}
            <div className="flex gap-2">
                <button
                    onClick={() => onView(record)}
                    className="flex-1 py-1.5 text-xs font-bold bg-slate-900 text-white rounded-lg hover:bg-slate-700 transition-all"
                >
                    결과 보기
                </button>
                <button
                    onClick={() => onRerun(record.idea)}
                    className="flex-1 py-1.5 text-xs font-bold border border-gray-200 text-gray-600 rounded-lg hover:border-gray-400 transition-all"
                >
                    🔄 재분석
                </button>
            </div>
        </div>
    );
}
