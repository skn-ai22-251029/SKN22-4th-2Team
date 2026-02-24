
import asyncio
import json
import os
import sys
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline import stage_5_vector_indexing
from src.config import PROCESSED_DATA_DIR, EMBEDDINGS_DIR

async def repair_and_index():
    # 1. Find latest files
    proc_files = list(PROCESSED_DATA_DIR.glob("processed_*.json"))
    embed_files = list(EMBEDDINGS_DIR.glob("embeddings_*.npz"))
    
    if not proc_files or not embed_files:
        print("Missing data files!")
        return

    latest_proc = max(proc_files, key=lambda p: p.stat().st_mtime)
    latest_embed = max(embed_files, key=lambda p: p.stat().st_mtime)
    
    print(f"Using Processed: {latest_proc}")
    print(f"Using Embeddings: {latest_embed}")
    
    # 2. Load and Repair
    with open(latest_proc, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    repaired_count = 0
    for item in data:
        claims = item.get("claims", [])
        if not claims or len(claims) == 0:
            # REPAIR: Use Abstract
            abstract = item.get("abstract", "")
            if abstract:
                print(f"Repairing ID {item.get('publication_number')}: Copying Abstract to Claims")
                item["claims"] = [{"claim_text": f"[WARNING: CLAIMS MISSING - SUBSTITUTED WITH ABSTRACT]\n{abstract}"}]
                repaired_count += 1
            else:
                print(f"ID {item.get('publication_number')} has NO claims and NO abstract!")
    
    if repaired_count == 0:
        print("No patents needed repair.")
    else:
        print(f"Repaired {repaired_count} patents.")
        
        # Save repaired file
        repaired_path = PROCESSED_DATA_DIR / "processed_repaired.json"
        with open(repaired_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Saved repaired data to {repaired_path}")
        
        # 3. Re-index
        print("Starting Re-indexing...")
        await stage_5_vector_indexing(repaired_path, latest_embed)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(repair_and_index())
