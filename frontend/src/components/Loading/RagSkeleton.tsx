

interface RagSkeletonProps {
    lines?: number;
}

export function RagSkeleton({ lines = 3 }: RagSkeletonProps) {
    return (
        <div className="w-full max-w-2xl mx-auto p-4 bg-white rounded-lg shadow-sm border border-gray-100">
            <div className="space-y-3">
                {Array.from({ length: lines }).map((_, i) => (
                    <div
                        key={i}
                        className="skeleton-loader h-4"
                        style={{ width: `${Math.max(60, 100 - (i * 15))}%` }}
                    />
                ))}
            </div>
        </div>
    );
}
