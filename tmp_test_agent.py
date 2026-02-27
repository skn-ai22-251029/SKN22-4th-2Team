import os
import asyncio

os.environ["OPENAI_API_KEY"] = "sk-dummy-1234567890"
os.environ["PINECONE_API_KEY"] = "dummy-pinecone-key"
os.environ["PINECONE_ENVIRONMENT"] = "gcp-starter"
os.environ["PINECONE_INDEX_NAME"] = "patent-index"
os.environ["APP_ENV"] = "local"

from src.patent_agent import PatentAgent

async def test():
    print("Testing PatentAgent direct...")
    agent = PatentAgent()
    print("Agent init done.")
    try:
        from unittest.mock import MagicMock
        history = MagicMock()
        
        result = await agent.analyze(
            user_idea="test idea",
            use_hybrid=False,
            stream=False
        )
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
