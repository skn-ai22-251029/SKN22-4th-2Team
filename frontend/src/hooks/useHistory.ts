import { useState, useEffect, useCallback } from 'react';
import { HistoryRecord } from '../types/rag';
import { getSessionId } from './useSessionId';

interface UseHistoryResult {
    records: HistoryRecord[];
    isLoading: boolean;
    error: string | null;
    refresh: () => void;
}

/**
 * useHistory.ts
 * 세션 기반 검색 히스토리 데이터 페치 훅
 * GET /api/history?session_id={id} 엔드포인트를 호출합니다.
 *
 * [백엔드 협업 필요]
 * - GET /api/history?session_id={id}
 * - 응답: HistoryRecord[] 배열
 */
export function useHistory(): UseHistoryResult {
    const [records, setRecords] = useState<HistoryRecord[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchHistory = useCallback(async () => {
        const sessionId = getSessionId();
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            // [11번 리뷰 반영] Critical: 세션 ID URL 노출 제거
            // ?session_id=... 쿼리파라미터는 브라우저 히스토리/서버 로그에 노드되므로
            // X-Session-ID 헤더만 사용하도록 백엔드와 협의합니다.
            const response = await fetch(`${apiUrl}/api/history`, {
                headers: {
                    'X-Session-ID': sessionId,
                }
            });

            if (!response.ok) {
                if (response.status === 404) {
                    // 히스토리가 없는 경우는 정상 (빈 배열 처리)
                    setRecords([]);
                    return;
                }
                throw new Error('히스토리를 불러오지 못했습니다.');
            }

            const data: HistoryRecord[] = await response.json();
            // 최신순 정렬
            setRecords(data.sort((a, b) =>
                new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
            ));
        } catch (err: any) {
            console.error('useHistory fetch error:', err);
            // [11번 리뷰 반영] Info: 개발 환경에서는 에러를 사용자에게 표시
            if (import.meta.env.DEV) {
                setError(err.message);
            }
            // 프로덕션에서는 Graceful Fallback: 빈 목록 표시
            setRecords([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    return { records, isLoading, error, refresh: fetchHistory };
}
