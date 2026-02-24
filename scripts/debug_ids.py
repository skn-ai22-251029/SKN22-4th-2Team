
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
    
    agent = PatentAgent()
    
    with open("debug_ids.txt", "w", encoding="utf-8") as out:
        for i in range(3): # Check first 3 samples
            sample = dataset[i]
            target_id = sample['anchor_patent_id']
            query = sample['query']
            
            out.write(f"\nSample {i}:\n")
            out.write(f"Query: {query}\n")
            out.write(f"Target: {target_id}\n")
            
            embedding = await agent.embed_text(query)
            res = await agent.db_client.async_search(embedding, top_k=5)
            
            out.write("Results:\n")
            if not res:
                out.write("  (No results)\n")
            for r in res:
                title = r.metadata.get('title', 'No Title') if r.metadata else 'No Title'
                out.write(f"  - {r.patent_id} (Score: {r.score:.4f}) | Title: {title}\n")

if __name__ == "__main__":
    asyncio.run(debug())
