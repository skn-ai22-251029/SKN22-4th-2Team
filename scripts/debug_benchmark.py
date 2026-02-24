
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PROCESSED_DATA_DIR
from src.patent_agent import PatentAgent

async def debug():
    files = list(PROCESSED_DATA_DIR.glob("selfrag_training_*.json"))
    latest_file = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    sample = dataset[0]
    target_id = sample['anchor_patent_id']
    query = sample['query']
    
    print(f"Target ID: '{target_id}'")
    
    agent = PatentAgent()
    embedding = await agent.embed_text(query)
    res = await agent.db_client.async_search(embedding, top_k=5)
    
    print("Search Results IDs:")
    for r in res:
        print(f" - '{r.patent_id}'")
        
    if any(r.patent_id == target_id for r in res):
        print("MATCH FOUND!")
    else:
        print("NO MATCH.")

if __name__ == "__main__":
    asyncio.run(debug())
