import os
import sys

# 필요한 환경 변수 세팅 (ECS Native Injection 시뮬레이션)
os.environ["OPENAI_API_KEY"] = "sk-dummy-1234567890"
os.environ["PINECONE_API_KEY"] = "dummy-pinecone-key"
os.environ["PINECONE_ENVIRONMENT"] = "gcp-starter"
os.environ["PINECONE_INDEX_NAME"] = "patent-index"
os.environ["APP_ENV"] = "production"

from src.api.main import app
from fastapi.testclient import TestClient
from src.api.dependencies import get_patent_agent
from unittest.mock import MagicMock

class MockPatentAgent:
    async def search_with_grading(self, idea, use_hybrid=False, ipc_filters=None):
        mock_result = MagicMock()
        mock_result.publication_number = "TEST-12345"
        mock_result.title = "Mocked Patent"
        mock_result.abstract = "This is a mock"
        mock_result.claims = "No claims"
        mock_result.grading_score = 80
        mock_result.grading_reason = "Mock reason"
        mock_result.dense_score = 0.8
        mock_result.sparse_score = 0.0
        mock_result.rrf_score = 0.8
        return [mock_result]
        
    async def critical_analysis_stream(self, idea, search_results):
        yield "Mocked stream chunk 1. "
        yield "Mocked stream chunk 2."

def mock_get_patent_agent():
    return MockPatentAgent()

app.dependency_overrides[get_patent_agent] = mock_get_patent_agent

client = TestClient(app)

def run_test():
    print("=== Testing Streaming API ===")
    with client.stream("POST", "/api/v1/analyze", json={
        "user_idea": "This is a proper test idea for validation.",
        "use_hybrid": False,
        "stream": True
    }) as response:
        print("Status Code:", response.status_code)
        for line in response.iter_lines():
            if line:
                print("Event:", line)

if __name__ == "__main__":
    run_test()
