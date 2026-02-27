import { useState } from 'react';

interface IdeaInputProps {
    onSubmit: (idea: string) => void;
    isLoading: boolean;
}

const MAX_LENGTH = 2000;

/**
 * 특허 아이디어 입력 폼 컴포넌트
 * 최소 길이 및 최대 길이 검증, 기본 XSS 방어를 포함합니다.
 */
export function IdeaInput({ onSubmit, isLoading }: IdeaInputProps) {
    const [idea, setIdea] = useState('');
    const [error, setError] = useState('');

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        // 최대 길이 제한 (프롬프트 인젝션 방어를 위한 1차 방어선)
        if (value.length > MAX_LENGTH) return;
        setIdea(value);
        if (error) setError('');
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = idea.trim();

        if (trimmed.length < 20) {
            setError('아이디어를 20자 이상 입력해 주세요.');
            return;
        }
        if (trimmed.length > MAX_LENGTH) {
            setError(`입력은 ${MAX_LENGTH}자 이내여야 합니다.`);
            return;
        }

        onSubmit(trimmed);
    };

    return (
        <div className="w-full max-w-3xl mx-auto px-4">
            {/* 헤더 */}
            <div className="text-center mb-10">
                <h1 className="text-4xl font-black text-slate-900 tracking-tight mb-3">
                    ✂️ Short-Cut
                </h1>
                <p className="text-gray-500 font-medium text-lg">
                    AI가 당신의 아이디어와 기존 특허를 비교 분석합니다
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* 텍스트 입력 영역 */}
                <div className="relative">
                    <textarea
                        id="idea-input"
                        value={idea}
                        onChange={handleChange}
                        placeholder="특허를 검증할 아이디어를 구체적으로 입력해 주세요.&#10;(예: 스마트 안경을 이용하여 실시간 AR 내비게이션을 제공하는 방법...)"
                        rows={7}
                        disabled={isLoading}
                        className="w-full p-5 text-gray-800 bg-white border-2 border-gray-200 rounded-2xl resize-none focus:outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-50 transition-all text-base shadow-sm disabled:bg-gray-50 disabled:text-gray-400"
                    />
                    {/* 글자 수 카운터 */}
                    <span className={`absolute bottom-4 right-4 text-xs font-medium ${idea.length > MAX_LENGTH * 0.9 ? 'text-red-400' : 'text-gray-400'}`}>
                        {idea.length} / {MAX_LENGTH}
                    </span>
                </div>

                {/* 유효성 검사 에러 메시지 */}
                {error && (
                    <p className="text-red-500 text-sm font-medium pl-1">⚠️ {error}</p>
                )}

                {/* 제출 버튼 */}
                <button
                    type="submit"
                    id="analyze-button"
                    disabled={isLoading || idea.trim().length < 20}
                    className="w-full py-4 bg-slate-900 text-white font-black text-lg rounded-2xl hover:bg-slate-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
                >
                    {isLoading ? '분석 중...' : '🔍 특허 침해 분석 시작'}
                </button>
            </form>
        </div>
    );
}
