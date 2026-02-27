/**
 * useSessionId.ts
 * 클라이언트 세션 ID 생성 및 관리 유틸 + React 훅
 *
 * [리뷰 반영 사항 - 06_session_id_hooks_review.md]
 * - Critical 1: 모듈 전역 변수를 SSR 환경에서 실행되지 않도록 방어 처리
 * - Critical 2: useSessionId를 React useState 기반으로 수정 (생명주기 연동)
 * - Warning: localStorage 가용성 결과를 최초 1회만 평가하여 캐싱
 * - Info: localStorage 가용성 체크를 모듈 레벨 즉시 실행으로 1회 캐싱
 */

import { useState, useCallback } from 'react';

const SESSION_KEY = 'shortcut_session_id';

// X-Session-ID 헤더명 상수로 분리 (오타 방지)
export const HEADER_SESSION_ID = 'X-Session-ID';

/**
 * localStorage 가용성을 모듈 로드 시 1회만 평가하여 캐싱
 * (매 호출마다 평가하지 않도록 최적화)
 *
 * SSR 환경 방어: typeof window === 'undefined' 체크로 서버에서는 절대 실행 안 됨
 */
const LS_AVAILABLE: boolean = (() => {
    // SSR 환경 방어 가드: 서버에서는 window 객체가 없음
    if (typeof window === 'undefined') return false;
    try {
        const testKey = '__shortcut_ls_test__';
        window.localStorage.setItem(testKey, '1');
        window.localStorage.removeItem(testKey);
        return true;
    } catch {
        return false;
    }
})();

/**
 * 메모리 폴백용 변수 (시크릿 모드 등 localStorage 차단 시 사용)
 *
 * [08번 리뷰 반영] Info: CSR 전용 변수임을 명시
 * - 이 변수는 Vite + CSR 환경에서만 안전하게 사용됩니다.
 * - SSR(서버 사이드 렌더링) 환경에서는 LS_AVAILABLE=false로 인해
 *   서버 프로세스 간 모듈 캐시가 공유될 위험이 있으나,
 *   LS_AVAILABLE IIFE의 typeof window 가드로 서버에서는 실행이 차단됩니다.
 * - 시크릿 모드에서는 탭을 닫으면 ID가 사라지는 한계가 있습니다 (브라우저 정책).
 */
let _inMemorySessionId: string | null = null;

/**
 * 기존 세션 ID를 조회하거나 신규 생성 후 반환하는 순수 유틸 함수
 * - 정상 환경: localStorage에 영구 저장
 * - 시크릿 모드 등: 메모리 일회성 ID 반환
 */
export const getSessionId = (): string => {
    if (LS_AVAILABLE) {
        const existing = localStorage.getItem(SESSION_KEY);
        if (existing) return existing;

        const newId = crypto.randomUUID();
        localStorage.setItem(SESSION_KEY, newId);
        return newId;
    } else {
        // 시크릿 모드 폴백: 메모리 변수에 저장 (탭 닫으면 초기화)
        if (!_inMemorySessionId) {
            _inMemorySessionId = crypto.randomUUID();
        }
        return _inMemorySessionId;
    }
};

/**
 * 세션 ID를 강제 재발급 (서버에서 세션 만료가 발생했을 때 호출)
 * localStorage의 기존 ID를 삭제하고 새 UUID를 생성합니다.
 * @returns 새로 발급된 세션 ID
 */
export const refreshSessionId = (): string => {
    if (LS_AVAILABLE) {
        localStorage.removeItem(SESSION_KEY);
    } else {
        _inMemorySessionId = null;
    }
    return getSessionId();
};

/**
 * React 세션 ID 훅 (useState로 React 생명주기와 명시적 연동)
 *
 * [리뷰 반영] Critical 2: useState(() => getSessionId())로 초기화하여
 * React 렌더링 사이클 내에서 안정적으로 동작하도록 수정
 *
 * @returns [sessionId, resetSessionId] - 현재 세션 ID와 재발급 함수
 */
export const useSessionId = (): [string, () => void] => {
    const [sessionId, setSessionId] = useState<string>(() => getSessionId());

    // [리뷰 반영] Warning: useCallback으로 감싸 매 렌더마다 재생성 방지 (무한 루프 위험 해소)
    const resetSessionId = useCallback(() => {
        const newId = refreshSessionId();
        setSessionId(newId);
    }, []); // refreshSessionId는 순수 유틸 함수이므로 의존성 없음

    return [sessionId, resetSessionId];
};
