
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import PROCESSED_DATA_DIR

def inspect():
    files = list(PROCESSED_DATA_DIR.glob("selfrag_training_*.json"))
    latest_file = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open("dataset_keys.txt", "w") as f:
        f.write(str(list(data[0].keys())))

if __name__ == "__main__":
    inspect()
