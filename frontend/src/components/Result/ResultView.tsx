import { PatentContext } from '../../types/rag';

interface PatentCardProps {
    patent: PatentContext;
    rank: number;
}

/**
 * 유사도 점수에 따른 색상 코딩 시스템
 * 🔴 높음 (80%~), 🟡 중간 (50~79%), 🟢 낮음 (~49%)
 */
function getRiskBadge(similarity: number): {
    label: string;
    className: string;
    icon: string;
} {
    if (similarity >= 80) {
        return { label: '높음', className: 'bg-red-100 text-red-700 border-red-200', icon: '🔴' };
    } else if (similarity >= 50) {
        return { label: '중간', className: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: '🟡' };
    } else {
        return { label: '낮음', className: 'bg-green-100 text-green-700 border-green-200', icon: '🟢' };
    }
}

/**
 * 특허 유사도 카드 컴포넌트
 * 특허 번호, 제목, 유사도 점수, 요약 정보를 시각화합니다.
 */
function PatentCard({ patent, rank }: PatentCardProps) {
    const badge = getRiskBadge(patent.similarity);

    return (
        <div className="p-5 border-2 border-gray-100 rounded-xl hover:border-blue-100 hover:shadow-md transition-all group break-inside-avoid">
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-gray-300">#{rank}</span>
                    <span className="text-sm font-bold text-gray-700 font-mono">{patent.id}</span>
                </div>
                <div className="flex items-center gap-2">
                    {/* 유사도 뱃지 */}
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${badge.className}`}>
                        {badge.icon} {badge.label} · {patent.similarity}%
                    </span>
                </div>
            </div>

            {/* 특허 제목 */}
            <h4 className="text-base font-bold text-gray-800 mb-2 group-hover:text-blue-700 transition-colors line-clamp-2">
                {patent.title}
            </h4>

            {/* 위험 사유 요약 */}
            <p className="text-sm text-gray-500 leading-relaxed line-clamp-3 mb-3">
                {patent.summary}
            </p>

            {/* KIPRIS 원문 링크 (Backend에서 patent.url 제공 시 동적 연결 예정) */}
            <div className="pt-2 border-t border-gray-50">
                <span className="text-xs text-gray-300 italic">
                    📌 원문 링크: 백엔드에서 patent.url 필드 제공 시 연결 예정
                </span>
            </div>
        </div>
    );
}

interface ResultViewProps {
    riskLevel: 'Low' | 'Medium' | 'High';
    riskScore: number;
    similarCount: number;
    uniqueness: string;
    topPatents: PatentContext[];
    onReset: () => void;
    onExportPdf?: () => void;
}

const RISK_CONFIG = {
    High: {
        gradient: 'from-red-900 to-red-700',
        badge: 'bg-red-500/30 text-red-100 border-red-400/30',
        label: '🔴 높은 침해 위험',
        desc: '기존 특허와 매우 유사합니다'
    },
    Medium: {
        gradient: 'from-yellow-800 to-amber-700',
        badge: 'bg-yellow-500/30 text-yellow-100 border-yellow-400/30',
        label: '🟡 부분적 유사성',
        desc: '부분적 유사성이 확인됩니다'
    },
    Low: {
        gradient: 'from-green-900 to-emerald-700',
        badge: 'bg-green-500/30 text-green-100 border-green-400/30',
        label: '🟢 낮은 침해 위험',
        desc: '독창성이 확인됩니다'
    }
};

/**
 * RAG 분석 결과 뷰 컴포넌트
 * 침해 위험도, 유사도 컬러 코딩, 유사 특허 목록을 시각화합니다.
 */
export function ResultView({
    riskLevel,
    riskScore,
    similarCount,
    uniqueness,
    topPatents,
    onReset,
    onExportPdf
}: ResultViewProps) {
    const risk = RISK_CONFIG[riskLevel];

    return (
        <div id="result-view" className="w-full max-w-4xl mx-auto mt-6 animate-in fade-in duration-500">
            {/* 결과 헤더 */}
            <div className={`bg-gradient-to-br ${risk.gradient} rounded-t-2xl p-8 text-white shadow-xl`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <p className="text-white/70 text-sm font-medium mb-1">특허 침해 분석 결과</p>
                        <h2 className="text-3xl font-black">{risk.label}</h2>
                        <p className="text-white/80 mt-1">{risk.desc}</p>
                    </div>
                    <div className="flex flex-col items-center bg-white/10 rounded-2xl px-8 py-4 border border-white/20 min-w-[120px]">
                        <span className="text-5xl font-black">{riskScore}<span className="text-2xl">%</span></span>
                        <span className="text-white/70 text-xs mt-1">위험도 점수</span>
                    </div>
                </div>
                {/* 요약 통계 */}
                <div className="mt-6 flex gap-4 flex-wrap">
                    <span className={`px-4 py-2 rounded-full border text-sm font-bold ${risk.badge}`}>
                        📄 유사 특허 {similarCount}건 발견
                    </span>
                </div>
            </div>

            {/* 결과 본문 */}
            <div className="bg-white p-8 rounded-b-2xl shadow-xl border border-gray-100/50">
                {/* 핵심 차별성 */}
                {uniqueness && (
                    <section className="mb-8 p-5 bg-blue-50 rounded-xl border border-blue-100">
                        <h3 className="text-sm font-black text-blue-700 uppercase tracking-wider mb-2">💡 핵심 차별성 분석</h3>
                        <p className="text-gray-700 leading-relaxed">{uniqueness}</p>
                    </section>
                )}

                {/* 유사 특허 목록 */}
                <section>
                    <h3 className="text-lg font-black text-gray-800 mb-4">
                        🔍 유사 특허 목록 ({topPatents.length}건)
                    </h3>
                    {topPatents.length === 0 ? (
                        <div className="text-center py-12 text-gray-400">
                            <div className="text-5xl mb-4">📭</div>
                            <p className="font-medium">유사 특허가 발견되지 않았습니다</p>
                            <p className="text-sm mt-1">독창적인 아이디어입니다!</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-4">
                            {topPatents.map((patent, index) => (
                                <PatentCard key={patent.id} patent={patent} rank={index + 1} />
                            ))}
                        </div>
                    )}
                </section>

                {/* 액션 버튼 영역 */}
                <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                        onClick={onReset}
                        className="px-8 py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-700 transition-all shadow-md"
                    >
                        🔄 다시 분석하기
                    </button>
                    {onExportPdf && (
                        <button
                            onClick={onExportPdf}
                            className="px-8 py-3 bg-white text-slate-900 font-bold rounded-xl border-2 border-slate-200 hover:border-slate-400 transition-all"
                        >
                            📄 PDF 내보내기
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
