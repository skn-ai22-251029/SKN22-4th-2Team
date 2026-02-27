import { useState } from 'react';
import { ProgressStepper } from './components/Loading/ProgressStepper';
import { RagSkeleton } from './components/Loading/RagSkeleton';
import { IdeaInput } from './components/Form/IdeaInput';
import { ResultView } from './components/Result/ResultView';
import { useRagStream } from './hooks/useRagStream';

function App() {
    const [idea, setIdea] = useState('');

    // RAG 상태 관리 훅
    const {
        isAnalyzing,
        isSkeletonVisible,
        isComplete,
        percent,
        message,
        resultData,
        startAnalysis,
        cancelAnalysis,
        setIsComplete
    } = useRagStream();

    const handleSubmitIdea = (inputIdea: string) => {
        setIdea(inputIdea);
        startAnalysis(inputIdea);
    };

    const handleReset = () => {
        setIdea('');
        setIsComplete(false);
    };

    return (
        <main className="min-h-screen p-8 flex flex-col items-center bg-gray-50">
            <h1 className="text-4xl font-extrabold text-blue-900 mb-2">💡 쇼특허 (Short-Cut) AI</h1>
            <p className="text-gray-500 mb-10 font-medium">아이디어만 입력하면 AI가 실시간으로 특허 침해 여부를 분석해 드립니다.</p>

            {/* 1. 분석 완료 후 결과 화면 */}
            {isComplete && resultData ? (
                <ResultView
                    idea={idea}
                    resultData={resultData}
                    onReset={handleReset}
                />
            ) : (
                /* 2. 메인 입력 및 로딩 화면 래퍼 */
                <div className="w-full max-w-3xl">
                    <IdeaInput
                        onSubmit={handleSubmitIdea}
                        disabled={isAnalyzing}
                    />

                    {isAnalyzing && (
                        <div className="mt-8">
                            <ProgressStepper
                                percent={percent}
                                message={message}
                                onCancel={cancelAnalysis}
                            />

                            {isSkeletonVisible ? (
                                <RagSkeleton lines={5} />
                            ) : (
                                <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-xl shadow-md border border-gray-100 mt-6 min-h-[160px]">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                                        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">AI Streaming</h3>
                                    </div>
                                    <p className="text-gray-700 leading-relaxed font-mono">가상 LLM 스트리밍 텍스트 렌더링 시작됨... ▌</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </main>
    );
}

export default App;
