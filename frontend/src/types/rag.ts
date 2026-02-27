export interface PatentContext {
    id: string; // 특허 번호
    similarity: number; // 유사도 (%)
    title: string; // 특허 제목
    summary: string; // 특허 요약 (위험 사유 등)
}

export interface RagAnalysisResult {
    riskLevel: 'Low' | 'Medium' | 'High'; // 침해 위험도
    riskScore: number; // 침해 위험도 점수 (%)
    similarCount: number; // 발견된 유사 특허 수
    uniqueness: 'Low' | 'Medium' | 'High'; // 핵심 차별성 수준
    topPatents: PatentContext[]; // 상위 유사 특허 리스트
}

export interface RagStreamState {
    isAnalyzing: boolean;
    isSkeletonVisible: boolean;
    isComplete: boolean;
    percent: number;
    message: string;
    resultData: RagAnalysisResult | null;
}
