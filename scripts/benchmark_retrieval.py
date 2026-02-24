
import sys
import asyncio
import json
import numpy as np
from pathlib import Path
from tqdm.asyncio import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import PROCESSED_DATA_DIR
from src.patent_agent import PatentAgent

async def benchmark():
    # 1. Load Dataset
    files = list(PROCESSED_DATA_DIR.glob("selfrag_training_*.json"))
    if not files:
        print("Error: No dataset found.")
        return
        
    latest_file = max(files, key=lambda p: p.stat().st_mtime)
    print(f"📂 Loading Dataset: {latest_file.name}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    print(f"   Total Samples: {len(dataset)}")
    
    # 2. Init Agent
    print("🤖 Initializing Patent Agent...")
    agent = PatentAgent()
    
    # 3. Benchmark Loop
    results = {
        "dense": 0,
        "sparse": 0,
        "hybrid": 0
    }
    
    total = len(dataset)
    
    print("🚀 Starting Benchmark (Dense / Sparse / Hybrid)...")
    
    def normalize_id(pid):
        return pid.replace("-", "").replace(" ", "").upper().strip()

    for sample in tqdm(dataset):
        query = sample['query']
        target_id = normalize_id(sample['anchor_patent_id'])
        
        # A. Embed Query
        embedding = await agent.embed_text(query)
        
        # B. Dense Search (Pinecone Only)
        dense_res = await agent.db_client.async_search(embedding, top_k=5)
        dense_ids = [normalize_id(r.patent_id) for r in dense_res]
        if target_id in dense_ids:
            results["dense"] += 1
            
        # C. Sparse Search
        sparse_res = await agent.db_client.async_hybrid_search(
            embedding, 
            query_text=query, 
            top_k=5,
            dense_weight=0.0,
            sparse_weight=1.0
        )
        sparse_ids = [normalize_id(r.patent_id) for r in sparse_res]
        if target_id in sparse_ids:
            results["sparse"] += 1
            
        # D. Hybrid Search (Standard)
        hybrid_res = await agent.db_client.async_hybrid_search(
            embedding,
            query_text=query,
            top_k=5,
            dense_weight=0.5,
            sparse_weight=0.5
        )
        hybrid_ids = [normalize_id(r.patent_id) for r in hybrid_res]
        if target_id in hybrid_ids:
            results["hybrid"] += 1
    
    # 4. Report
    print("\n📊 Benchmark Results (Recall@5):")
    print(f"   - Dense Only: {results['dense']/total*100:.1f}% ({results['dense']}/{total})")
    print(f"   - Sparse Only: {results['sparse']/total*100:.1f}% ({results['sparse']}/{total})")
    print(f"   - Hybrid (Score Fusion): {results['hybrid']/total*100:.1f}% ({results['hybrid']}/{total})")
    
    # Save results to file for the plot script to read? 
    # Or just print them and I will manually update.
    # I'll print them clearly.

if __name__ == "__main__":
    asyncio.run(benchmark())
