import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
from src.patent_agent import PatentAgent

# Sample 14 Query (contains explicit IDs)
SAMPLE_QUERY = """특허 CN-119935140-A의 청구항과 선행특허 CN-119622040-A의 
청구항을 비교 분석하세요. 유사도, 침해 리스크, 회피 전략을 포함해서 답변해주세요."""

TARGET_ID_1 = "CN-119935140-A"
TARGET_ID_2 = "CN-119622040-A"

@pytest.mark.asyncio
async def test_id_retrieval_stability():
    """Test if explicit IDs are consistently retrieved under load."""
    agent = PatentAgent()
    
    async def run_search(i):
        results = await agent.search_with_grading(SAMPLE_QUERY)
        
        found_ids = [r.publication_number for r in results]
        prioritized_ids = [r.publication_number for r in results if r.is_prioritized]
        
        print(f"[{i}] Found: {len(found_ids)}, Prioritized: {len(prioritized_ids)}")
        
        return {
            "found": found_ids,
            "prioritized": prioritized_ids
        }
    
    # Run 10 times concurrently to simulate load
    tasks = [run_search(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    for i, res in enumerate(results):
        assert TARGET_ID_1 in res["found"], f"Run {i}: {TARGET_ID_1} missing"
        assert TARGET_ID_2 in res["found"], f"Run {i}: {TARGET_ID_2} missing"
        assert TARGET_ID_1 in res["prioritized"], f"Run {i}: {TARGET_ID_1} not prioritized"
        assert TARGET_ID_2 in res["prioritized"], f"Run {i}: {TARGET_ID_2} not prioritized"

if __name__ == "__main__":
    asyncio.run(test_id_retrieval_stability())
