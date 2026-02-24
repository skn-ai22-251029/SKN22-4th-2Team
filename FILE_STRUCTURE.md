# 🗺️ Project File Structure (Short-Cut v3.0)

이 문서는 프로젝트의 각 파일 용도와 주요 함수/클래스를 정리한 로드맵입니다.

---

## 📂 Root Directory
메인 실행 파일 및 설정 파일들이 위치합니다.

| 파일명 | 용도 | 주요 내용 |
| :--- | :--- | :--- |
| `app.py` | **Streamlit 메인 앱** | UI 렌더링, 사용자 입력 처리, 전체 분석 파이프라인 호출 |
| `main.py` | CLI 실행 엔트리포인트 | 데이터 수집(BigQuery)부터 인덱싱까지의 전체 파이프라인 제어 |
| `requirements.txt` | 의존성 라이브러리 목록 | `pinecone-client`, `openai`, `sentence-transformers` 등 |
| `.env` | 환경 변수 설정 | API 키, DB 설정값 관리 (깃 비공개) |

---

## 📂 `src/` (Core Logic)
시스템의 핵심 비즈니스 로직이 담긴 폴더입니다.

### 🤖 Agent & Analysis
*   **`patent_agent.py`**: 프로젝트의 심장. Self-RAG 로직 구현.
    *   `generate_hypothetical_claim()`: HyDE (가상 청구항 생성)
    *   `search_multi_query()`: 멀티 쿼리 병렬 검색
    *   `grade_results()`: LLM 관련성 채점 (Critique)
    *   `rewrite_query()`: 검색 실패 시 쿼리 재작성 (Reflection)
*   **`analysis_logic.py`**: 분석 단계별 흐름 제어.
    *   `run_full_analysis()`: 전체 분석 시퀀스 오케스트레이션
*   **`reranker.py`**: 검색 결과 재정렬.
    *   `Reranker.rerank()`: Cross-Encoder를 사용한 정밀 랭킹

### 🗄️ Data & Database
*   **`vector_db.py`**: Pinecone 및 BM25 관리.
    *   `PineconeClient.hybrid_search()`: 밀집/희소 벡터 결합 검색
    *   `KeywordExtractor`: BM25용 키워드 추출기
*   **`bigquery_extractor.py`**: BigQuery에서 특허 추출.
    *   `BigQueryExtractor.fetch_patents()`: SQL 쿼리 실행 및 데이터 로드
*   **`pipeline.py`**: 데이터 가공 파이프라인.
    *   `PatentPipeline.run()`: 임베딩 및 Pinecone 업로드 자동화
*   **`history_manager.py`**: 검색 기록 관리.
    *   `HistoryManager.save_result()`: SQLite에 히스토리 저장

### 🛠️ Utilities
*   **`pdf_generator.py`**: 분석 결과 PDF 내보내기.
*   **`utils.py`**: 로깅, 텍스트 전처리 등 공통 유틸리티.
*   **`config.py`**: 프로젝트 전역 설정값 클래스화.

---

## 📂 `scripts/` (Maintenance)
운영 및 테스트를 위한 보조 스크립트들입니다.

| 파일명 | 용도 |
| :--- | :--- |
| `generate_presentation_plots.py` | 발표용 차트(HTML) 생성 |
| `benchmark_retrieval.py` | 검색 전략별 성능(Recall) 측정 |
| `repair_data.py` | 데이터 누락이나 오류 수정 (re-indexing) |
| `migrate_to_pinecone_hybrid.py` | 기존 인덱스를 하이브리드로 마이그레이션 |

---

## 📂 `tests/` (Verification)
검증을 위한 테스트 코드입니다.

| 파일명 | 용도 |
| :--- | :--- |
| `test_evaluation_golden.py` | Golden Dataset 기반 성능 평가 (Faithfulness 등) |
| `test_hybrid_search.py` | 하이브리드 검색의 정확도 및 가중치 테스트 |
| `test_parser.py` | 특허 문서 파싱 및 전처리 로직 검증 |

---

## 📊 Summary of Databases
- **Pinecone**: 메인 검색 엔진 (Vectors)
- **BigQuery**: 원천 데이터 소스 (Raw Data)
- **SQLite (`history.db`)**: 앱 내 사용자 히스토리 저장용
