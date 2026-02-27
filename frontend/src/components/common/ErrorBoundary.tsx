import { Component, ErrorInfo, ReactNode } from 'react';
import { ErrorFallback } from './ErrorFallback';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * 전역 에러 바운더리 컴포넌트
 * 렌더링 중 발생하는 JavaScript 에러를 캐치하여 Fallback UI를 표시합니다.
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary 에러 캐치:', error, errorInfo);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            return (
                <ErrorFallback
                    title="예기치 못한 오류가 발생했습니다"
                    message="페이지를 새로고침하거나 잠시 후 다시 시도해 주세요."
                    onRetry={this.handleRetry}
                />
            );
        }
        return this.props.children;
    }
}
