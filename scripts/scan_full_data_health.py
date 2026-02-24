
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import PROCESSED_DATA_DIR

def scan_data():
    # Find latest processed file (Original, not repaired)
    # We want to know the state of the data BEFORE my fix mostly, but checking the latest original file is best.
    files = list(PROCESSED_DATA_DIR.glob("processed_patents_AI_NLP_Search_*.json"))
    if not files:
        print("No processed files found.")
        return

    target_file = max(files, key=lambda p: p.stat().st_mtime)
    print(f"Scanning file: {target_file}")
    
    with open(target_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total = len(data)
    missing_claims = 0
    missing_abstract = 0
    missing_both = 0
    
    empty_abstract_ids = []
    
    for item in data:
        tid = item.get("publication_number", "UNKNOWN")
        claims = item.get("claims", [])
        abstract = item.get("abstract", "")
        
        has_claims = False
        if claims and len(claims) > 0:
            # Check if text is not empty
            if isinstance(claims[0], dict):
                 if claims[0].get("claim_text", "").strip(): has_claims = True
            elif isinstance(claims[0], str):
                 if claims[0].strip(): has_claims = True
        
        has_abstract = True if abstract and abstract.strip() else False
        
        if not has_claims:
            missing_claims += 1
            
        if not has_abstract:
            missing_abstract += 1
            empty_abstract_ids.append(tid)
            
        if not has_claims and not has_abstract:
            missing_both += 1

    print(f"\n{'='*40}")
    print(f"DATA HEALTH REPORT")
    print(f"{'='*40}")
    print(f"Total Patents: {total}")
    print(f"Missing Claims: {missing_claims} ({(missing_claims/total)*100:.1f}%)")
    print(f"Missing Abstract: {missing_abstract} ({(missing_abstract/total)*100:.1f}%)")
    print(f"Missing BOTH (Critical): {missing_both}")
    print(f"{'='*40}")
    
    if empty_abstract_ids:
        print(f"IDs with Missing Abstract ({len(empty_abstract_ids)}):")
        print(empty_abstract_ids[:10]) # Show first 10
        if len(empty_abstract_ids) > 10: print("...")

if __name__ == "__main__":
    scan_data()
