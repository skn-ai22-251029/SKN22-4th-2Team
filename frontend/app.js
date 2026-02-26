document.addEventListener('DOMContentLoaded', () => {
    // API Configurations (백엔드와 통합 서빙을 위해 상대 경로 사용 권장)
    const API_BASE_URL = window.ENV?.API_BASE_URL || '/api/v1';

    // Hardcoded User ID for testing, ideally should come from auth
    const USER_ID = 'test_user_webapp'; // TODO: 추후 JWT Authorization 인증 헤더로 교체 필요

    // DOM Elements
    const form = document.getElementById('analyze-form');
    const ideaInput = document.getElementById('idea-input');
    const charCount = document.getElementById('char-count');
    const ideaError = document.getElementById('idea-error');
    const categoryTags = document.querySelectorAll('.category-tag');
    const submitBtn = document.getElementById('submit-btn');
    const useHybridCheckbox = document.getElementById('use-hybrid');

    const resultContainer = document.getElementById('result-container');
    const logOutput = document.getElementById('log-output');
    const statusBadge = document.getElementById('status-badge');

    const historyContainer = document.getElementById('history-container');
    const emptyHistory = document.getElementById('empty-history');

    // State
    const MIN_CHARS = 10;
    const MAX_CHARS = 500;
    let selectedCategories = new Set();
    let isAnalyzing = false;

    // 1. Initial Load: Fetch History
    fetchUserHistory();

    // 2. Event Listeners for Input Validation
    ideaInput.addEventListener('input', (e) => {
        const length = e.target.value.length;
        charCount.textContent = `${length} / ${MAX_CHARS}`;

        if (length > MAX_CHARS) {
            e.target.value = e.target.value.substring(0, MAX_CHARS);
            charCount.textContent = `${MAX_CHARS} / ${MAX_CHARS}`;
            charCount.classList.add('text-red-500');
        } else {
            charCount.classList.remove('text-red-500');
        }

        if (length > 0 && length < MIN_CHARS) {
            ideaError.classList.remove('hidden');
        } else {
            ideaError.classList.add('hidden');
        }
    });

    // 3. Category Tag Selection Logic
    categoryTags.forEach(tag => {
        tag.addEventListener('click', () => {
            const value = tag.dataset.value;
            if (selectedCategories.has(value)) {
                selectedCategories.delete(value);
                tag.classList.remove('active');
            } else {
                selectedCategories.add(value);
                tag.classList.add('active');
            }
        });
    });

    // 4. Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const ideaText = ideaInput.value.trim();

        // Final Validation Validation
        if (ideaText.length < MIN_CHARS) {
            ideaError.classList.remove('hidden');
            ideaInput.focus();
            return;
        }

        await startAnalysis(ideaText, Array.from(selectedCategories), useHybridCheckbox.checked);
    });

    // --- Core Functions ---

    /**
     * Fetch user history from API
     */
    async function fetchUserHistory() {
        try {
            // Path param -> Query parameter로 수정 (Review 피드백 반영)
            const res = await fetch(`${API_BASE_URL}/history?user_id=${USER_ID}`);
            if (!res.ok) throw new Error('히스토리를 불러오지 못했습니다.');

            const data = await res.json();
            renderHistory(data.history || []);
        } catch (error) {
            console.error('History fetch failed:', error);
            // Don't show UI error for history, just keep empty state
        }
    }

    /**
     * Render the history sidebar
     */
    function renderHistory(histories) {
        if (histories.length === 0) {
            emptyHistory.classList.remove('hidden');
            historyContainer.classList.add('hidden');
            return;
        }

        emptyHistory.classList.add('hidden');
        historyContainer.classList.remove('hidden');
        historyContainer.innerHTML = '';

        histories.forEach(item => {
            // item.idea_text -> item.user_idea로 매핑 필드 수정
            const textPreview = item.user_idea ? (item.user_idea.length > 40 ? item.user_idea.substring(0, 40) + '...' : item.user_idea) : '알 수 없는 아이디어';
            const dateStr = item.timestamp ? new Date(item.timestamp).toLocaleDateString() : '';

            const el = document.createElement('div');
            el.className = 'p-3 rounded-lg border border-slate-100 hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-colors bg-white shadow-sm';
            el.innerHTML = `
                <div class="text-xs text-slate-400 mb-1">${dateStr}</div>
                <div class="text-sm font-medium text-slate-700 line-clamp-2">${textPreview}</div>
            `;
            el.addEventListener('click', () => {
                if (isAnalyzing) return;
                ideaInput.value = item.user_idea || '';
                // Trigger input event to update char count
                ideaInput.dispatchEvent(new Event('input'));
                ideaInput.focus();
            });
            historyContainer.appendChild(el);
        });
    }

    /**
     * Start the analysis using SSE
     */
    async function startAnalysis(userIdea, ipcFilters, useHybrid) {
        // UI Updates for Loading state
        isAnalyzing = true;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="spinner"></div><span>분석 중...</span>';

        resultContainer.classList.remove('hidden');
        logOutput.innerHTML = '';
        statusBadge.textContent = '분석 진행 중...';
        statusBadge.className = 'px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full animate-pulse';

        // Prepare request body
        const reqBody = {
            user_idea: userIdea,
            user_id: USER_ID,
            use_hybrid: useHybrid,
            ipc_filters: ipcFilters.length > 0 ? ipcFilters : null
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60초 타임아웃 방어 로직 추가

        try {
            // Using fetch to read SSE stream
            const response = await fetch(`${API_BASE_URL}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(reqBody),
                signal: controller.signal
            });

            if (!response.ok) {
                if (response.status === 429) {
                    throw new Error('요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.');
                }
                if (response.status === 403) {
                    try {
                        const errData = await response.json();
                        throw new Error(errData.detail || '허용되지 않은 악의적 검색어입니다.');
                    } catch (e) {
                        throw new Error('허용되지 않은 악의적 검색어입니다.');
                    }
                }
                throw new Error(`API 오류: ${response.status}`);
            }

            // Read the SSE stream manually via body reader since we did POST
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Keep the last partial line in the buffer
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.trim() === '') continue;
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6);
                        if (dataStr === '[DONE]') {
                            break;
                        }

                        try {
                            const eventData = JSON.parse(dataStr);
                            appendLogEvent(eventData);
                        } catch (e) {
                            console.error("Failed to parse SSE data:", dataStr);
                        }
                    }
                }
            }

            // Finish
            statusBadge.textContent = '분석 완료';
            statusBadge.className = 'px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full';

            // Refresh history
            fetchUserHistory();

        } catch (error) {
            console.error('Analysis failed:', error);
            let errorMessage = error.message;
            if (error.name === 'AbortError') {
                errorMessage = '응답 시간이 지연되어 요청이 취소되었습니다. 다시 시도해주세요.';
            }
            appendLogEvent({ type: 'error', message: errorMessage });
            statusBadge.textContent = '에러 발생';
            statusBadge.className = 'px-3 py-1 bg-red-100 text-red-700 text-xs font-bold rounded-full';
        } finally {
            clearTimeout(timeoutId);
            isAnalyzing = false;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>분석 시작하기</span><i class="fa-solid fa-arrow-right"></i>';
        }
    }

    /**
     * Append SSE log to output container
     */
    function appendLogEvent(event) {
        const el = document.createElement('div');

        // Render differently based on event type
        if (event.type === 'phase') {
            el.className = 'log-entry phase';
            el.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin mr-2 text-blue-500"></i> ${escapeHtml(event.message)}`;
        } else if (event.type === 'log') {
            el.className = 'log-entry text-slate-600';
            el.textContent = `> ${event.message}`;
        } else if (event.type === 'result') {
            el.className = 'log-entry result mt-4 mb-4';
            el.innerHTML = `
                <div class="font-bold mb-2 text-green-700"><i class="fa-solid fa-check-circle mr-1"></i> 분석 완료 결과 요약</div>
                <div class="whitespace-pre-wrap text-slate-700">${escapeHtml(event.data?.final_summary || '결과가 요약되지 않았습니다.')}</div>
            `;
        } else if (event.type === 'error') {
            el.className = 'log-entry error';
            el.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1"></i> ${escapeHtml(event.message)}`;
        } else {
            el.className = 'log-entry text-slate-500 text-xs';
            el.textContent = JSON.stringify(event);
        }

        logOutput.appendChild(el);
        // Auto scroll
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
