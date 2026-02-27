import { useState, useRef, useCallback } from 'react';
import { RagAnalysisResult } from '../types/rag';

export function useRagStream() {
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isSkeletonVisible, setIsSkeletonVisible] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [percent, setPercent] = useState(0);
    const [message, setMessage] = useState('');
    const [resultData, setResultData] = useState<RagAnalysisResult | null>(null);

    // 진행중인 fetch 요청을 취소하기 위한 AbortController
    const abortControllerRef = useRef<AbortController | null>(null);

    const startAnalysis = useCallback(async (idea: string) => {
        setIsAnalyzing(true);
        setIsSkeletonVisible(true);
        setIsComplete(false);
        setPercent(0);
        setMessage('네트워크 상의 특허 DB 연결을 시도합니다...');
        setResultData(null);

        // 이전 요청이 있다면 취소
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        try {
            // 백엔드 FastAPI SSE 엔드포인트 호출 (POST)
            const response = await fetch('http://localhost:8000/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream', // 불필요할 수 있으나 명시
                },
                body: JSON.stringify({ idea }),
                signal: abortController.signal
            });

            if (!response.ok || !response.body) {
                throw new Error(`서버 응답 오류 (Status: ${response.status})`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                // 청크 디코딩 후 버퍼에 누적 (데이터가 잘려서 올 수 있으므로)
                buffer += decoder.decode(value, { stream: true });

                // SSE 스트림 라인 단위(\n\n) 처리
                const lines = buffer.split('\n\n');

                // 마지막 묶음은 아직 불완전할 수 있으므로 다시 버퍼에 남김
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim() === '') continue;

                    // "event: progress\ndata: {...}" 형태의 SSE 파싱
                    const eventMatch = line.match(/event:\s*([^\n]+)/);
                    const dataMatch = line.match(/data:\s*([^\n]+)/);

                    let eventType = 'message';
                    let dataStr = '';

                    if (eventMatch && dataMatch) {
                        eventType = eventMatch[1].trim();
                        dataStr = dataMatch[1].trim();
                    } else if (line.startsWith('data:')) {
                        // event 지정 없이 data만 왔을 경우
                        dataStr = line.replace('data:', '').trim();
                    }

                    if (dataStr) {
                        try {
                            const parsedData = JSON.parse(dataStr);

                            // 스켈레톤 초기 숨김 처리
                            if (parsedData.percent >= 10) {
                                setIsSkeletonVisible(false);
                            }

                            if (eventType === 'progress') {
                                setPercent(parsedData.percent || 0);
                                setMessage(parsedData.message || '');
                            } else if (eventType === 'complete') {
                                setPercent(100);
                                setMessage('분석이 모두 완료되었습니다.');
                                setResultData(parsedData.result);

                                setTimeout(() => {
                                    setIsAnalyzing(false);
                                    setIsComplete(true);
                                }, 1500);
                            } else if (eventType === 'error') {
                                throw new Error(parsedData.detail || '스트림 처리 중 에러 발생');
                            }
                        } catch (e) {
                            console.error('SSE JSON Parsing Error:', e, 'Raw Data:', dataStr);
                        }
                    }
                }
            }
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log('Analysis request aborted by user');
            } else {
                console.error('Analysis failed:', error);
                alert(`특허 분석 실패: ${error.message}`);
                cancelAnalysis(); // 에러 시 상태 완전 초기화
            }
        } finally {
            abortControllerRef.current = null;
        }
    }, []);

    const cancelAnalysis = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setIsAnalyzing(false);
        setIsSkeletonVisible(false);
        setIsComplete(false);
        setPercent(0);
        setMessage('');
        setResultData(null);
    }, []);

    return {
        isAnalyzing,
        isSkeletonVisible,
        isComplete,
        percent,
        message,
        resultData,
        startAnalysis,
        cancelAnalysis,
        setIsComplete,
    };
}
