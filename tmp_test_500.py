import os
import sys

# Redirect stdout and stderr
sys.stdout = open("test_out.log", "w", encoding="utf-8")
sys.stderr = sys.stdout

os.environ["OPENAI_API_KEY"] = "sk-dummy-1234567890"
os.environ["PINECONE_API_KEY"] = "dummy-pinecone-key"
os.environ["PINECONE_ENVIRONMENT"] = "gcp-starter"
os.environ["PINECONE_INDEX_NAME"] = "patent-index"
os.environ["APP_ENV"] = "local"

from src.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_analyze():
    response = client.post(
        "/api/v1/analyze",
        json={
            "user_idea": "test idea",
            "use_hybrid": False,
            "stream": False # Let's test non-streaming first
        }
    )
    print("Non-streaming STATUS:", response.status_code)
    try:
        print("BODY:", response.json())
    except:
        print("BODY (text):", response.text)

if __name__ == "__main__":
    test_analyze()
