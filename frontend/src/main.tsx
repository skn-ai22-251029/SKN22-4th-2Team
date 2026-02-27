import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import App from './App';

const rootElement = document.getElementById('root');
if (!rootElement) {
    throw new Error('루트 DOM 요소(#root)를 찾을 수 없습니다. index.html을 확인해 주세요.');
}

createRoot(rootElement).render(
    <StrictMode>
        <ErrorBoundary>
            <App />
        </ErrorBoundary>
    </StrictMode>
);
