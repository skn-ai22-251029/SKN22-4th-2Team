import { useState, useRef, useEffect, useCallback } from 'react';
import { RagAnalysisResult } from '../types/rag';
import { useSessionId, HEADER_SESSION_ID } from './useSessionId';

// [11번 리뷰 반영] Critical: 에러 코드 필드 추가 — 문자열 비교 대신 코드 기반 판별
export type RagErrorCode =
    | 'RATE_LIMITED'
    | 'SESSION_EXPIRED'
    | 'TOKEN_EXCEEDED'
    | 'NOT_FOUND'
    | 'TIMEOUT'
    | 'NETWORK_ERROR';

export interface RagErrorInfo {
    code: RagErrorCode;  // 에러 종류 식별 코드
    title: string;
    message: string;
}

export function useRagStream() {
    // [리뷰 반영] Critical 2: useState 기반 useSessionId로 변경
    // resetSessionId() 호출 시 React 상태도 갱신되어 클로저 바인딩 문제 해소
    const [sessionId, resetSessionId] = useSessionId();

    // [08번 리뷰 반영] Warning: 언마운트 시 setState 호출 방지를 위한 마운트 감지 Ref
    const isMountedRef = useRef(true);
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isSkeletonVisible, setIsSkeletonVisible] = useState(false);
    const [isComplete, setIsComplete] = useState(false);
    const [percent, setPercent] = useState(0);
    const [message, setMessage] = useState('');
    const [resultData, setResultData] = useState<RagAnalysisResult | null>(null);
    const [errorInfo, setErrorInfo] = useState<RagErrorInfo | null>(null);

    // 진행중인 fetch 요청을 취소하기 위한 AbortController
    const abortControllerRef = useRef<AbortController | null>(null);

    const startAnalysis = useCallback(async (idea: string) => {
        setIsAnalyzing(true);
        setIsSkeletonVisible(true);
        setIsComplete(false);
        setPercent(0);
        setMessage('네트워크 상의 특허 DB 연결을 시도합니다...');
        setResultData(null);
        setErrorInfo(null);

        // 이전 요청이 있다면 취소
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        // 60초 완전 타임아웃 타이머
        // [리뷰 반영] Warning: isTimeout 플래그 기반으로 구형 브라우저 호환성 확보
        let isTimeout = false;
        const timeoutId = setTimeout(() => {
            if (abortControllerRef.current) {
                isTimeout = true; // 타임아웃 발생 명시 플래그
                abortControllerRef.current.abort(); // abort 이유 없이 순수 중단만
            }
        }, 60000);

        try {
            // 백엔드 FastAPI SSE 엔드포인트 호출 (POST)
            // 시니어 리뷰 반영: VITE_API_URL 환경변수 사용
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                    [HEADER_SESSION_ID]: sessionId, // 세션 식별자 헤더 자동 포함 (상수 사용)
                },
                body: JSON.stringify({ idea }),
                signal: abortController.signal
            });

            if (!response.ok) {
                // HTTP Status 분기 처리
                if (response.status === 401 || response.status === 419) {
                    // [리뷰 반영] Warning: resetSessionId()로 React 상태까지 갱신
                    // → 다음 startAnalysis 호출 시 새 sessionId가 클로저에 잡힘
                    resetSessionId();
                    throw new Error('SESSION_EXPIRED');
                } else if (response.status === 429) {
                    // [08번 리뷰 반영] Critical: Rate Limit 전용 에러 분기 추가
                    throw new Error('RATE_LIMITED');
                } else if (response.status === 413 || response.status === 422) {
                    throw new Error('TOKEN_EXCEEDED');
                } else if (response.status === 404) {
                    throw new Error('NOT_FOUND');
                } else {
                    throw new Error('NETWORK_ERROR');
                }
            }

            if (!response.body) {
                throw new Error('NETWORK_ERROR');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                // 청크 디코딩 후 버퍼에 누적
                buffer += decoder.decode(value, { stream: true });

                // SSE 스트림 라인 단위(\n\n) 처리
                const lines = buffer.split('\n\n');

                // 마지막 묶음은 아직 불완전할 수 있으므로 다시 버퍼에 남김
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim() === '') continue;

                    const eventMatch = line.match(/event:\s*([^\n]+)/);
                    const dataMatch = line.match(/data:\s*([^\n]+)/);

                    let eventType = 'message';
                    let dataStr = '';

                    if (eventMatch && dataMatch) {
                        eventType = eventMatch[1].trim();
                        dataStr = dataMatch[1].trim();
                    } else if (line.startsWith('data:')) {
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

                                // [08번 리뷰 반영] Warning: isMountedRef로 언마운트 시 setState 누수 방어
                                setTimeout(() => {
                                    if (isMountedRef.current) {
                                        setIsAnalyzing(false);
                                        setIsComplete(true);
                                    }
                                }, 1500);
                            } else if (eventType === 'empty' || parsedData.status === 'empty') {
                                throw new Error('NOT_FOUND');
                            } else if (eventType === 'error') {
                                throw new Error('NETWORK_ERROR');
                            }
                        } catch (e: any) {
                            if (e.message === 'NOT_FOUND' || e.message === 'NETWORK_ERROR') throw e;
                            console.error('SSE JSON Parsing Error:', e, 'Raw Data:', dataStr);
                        }
                    }
                }
            }
            clearTimeout(timeoutId);
        } catch (error: any) {
            clearTimeout(timeoutId);

            // AbortController.abort() 발생 시 (사용자 취소 또는 타임아웃)
            if (error.name === 'AbortError') {
                // [리뷰 반영] Warning: isTimeout 플래그로 타임아웃/취소 명확히 구분
                if (isTimeout) {
                    setErrorInfo({
                        code: 'TIMEOUT',
                        title: '분석 시간 초과 (Timeout) ⏱️',
                        message: '분석에 시간이 초과되었습니다. 입력을 줄여서 다시 시도해 주세요.'
                    });
                } else {
                    console.log('분석 요청이 사용자에 의해 취소되었습니다.');
                }
            } else {
                console.error('Analysis failed:', error);

                // [11번 리뷰 반영] Critical: code 필드 추가하여 에러 종류별 매핑
                if (error.message === 'SESSION_EXPIRED') {
                    setErrorInfo({
                        code: 'SESSION_EXPIRED',
                        title: '세션이 만료되었습니다 🔄',
                        message: '세션이 재발급되었습니다. 다시 시도해 주세요.'
                    });
                } else if (error.message === 'RATE_LIMITED') {
                    setErrorInfo({
                        code: 'RATE_LIMITED',
                        title: '분석 한도에 도달했습니다 🚦',
                        message: '오늘의 분석 횟수를 모두 사용하셨습니다. 잠시 후 다시 시도하거나 내일 다시 이용해 주세요.'
                    });
                } else if (error.message === 'TOKEN_EXCEEDED') {
                    setErrorInfo({
                        code: 'TOKEN_EXCEEDED',
                        title: '입력 텍스트가 너무 깁니다 🚫',
                        message: '입력하신 특허 아이디어가 백엔드 처리 한도를 초과했습니다.'
                    });
                } else if (error.message === 'NOT_FOUND') {
                    setErrorInfo({
                        code: 'NOT_FOUND',
                        title: '유사 특허 결과를 찾지 못했습니다 📭',
                        message: '입력하신 내용과 일치하는 선행 특허가 없습니다.'
                    });
                } else {
                    setErrorInfo({
                        code: 'NETWORK_ERROR',
                        title: '네트워크 연결 오류 🔌',
                        message: '일시적인 연결 문제가 발생했습니다. 백엔드 서버가 켜져 있는지 확인하고 잠시 후 다시 시도해 주세요.'
                    });
                }
            }

            // UI 상태 초기화로 Fallback 이나 기본화면 노출 유도
            setIsAnalyzing(false);
            setIsSkeletonVisible(false);
            setPercent(0);
        } finally {
            abortControllerRef.current = null;
        }
    }, [sessionId, resetSessionId]); // [리뷰 반영] Info: resetSessionId 의존성 추가

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
        setErrorInfo(null);
    }, []);

    return {
        isAnalyzing,
        isSkeletonVisible,
        isComplete,
        percent,
        message,
        resultData,
        errorInfo,
        startAnalysis,
        cancelAnalysis,
        setIsComplete,
        setErrorInfo,
        setResultData  // [11번 리뷰 반영] Critical: 히스토리 캐시 결과 직접 주입을 위해 노출
    };
}
