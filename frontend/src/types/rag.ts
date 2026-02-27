export interface PatentContext {
    id: string;        // 특허 번호
    similarity: number; // 유사도 (%)
    title: string;     // 특허 제목
    summary: string;   // 특허 요약 (위험 사유 등)
}

export interface RagAnalysisResult {
    riskLevel: 'Low' | 'Medium' | 'High'; // 침해 위험도
    riskScore: number;                     // 침해 위험도 점수 (%)
    similarCount: number;                  // 발견된 유사 특허 수
    uniqueness: string;                    // 핵심 차별성 설명
    topPatents: PatentContext[];           // 상위 유사 특허 리스트
}

export interface RagStreamState {
    isAnalyzing: boolean;
    isSkeletonVisible: boolean;
    isComplete: boolean;
    percent: number;
    message: string;
    resultData: RagAnalysisResult | null;
}

// [#25 추가] 검색 히스토리 레코드 타입
export interface HistoryRecord {
    id: string;                            // 분석 고유 ID (서버 발급)
    idea: string;                          // 입력한 아이디어 요약 (최대 50자)
    riskLevel: 'Low' | 'Medium' | 'High'; // 침해 위험도
    riskScore: number;                     // 침해 위험도 점수 (%)
    similarCount: number;                  // 유사 특허 수
    createdAt: string;                     // 분석 일시 (ISO 8601)
    result?: RagAnalysisResult;            // 과거 결과 데이터 (캐시, 선택적)
}

