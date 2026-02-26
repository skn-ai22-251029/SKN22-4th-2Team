"""
JSON serialization utility module.
Uses orjson if available for performance, falls back to standard json.
"""
from typing import Any

try:
    import orjson
    def json_loads(s: str) -> Any: 
        return orjson.loads(s)
    def json_dumps(o: Any) -> str: 
        return orjson.dumps(o).decode('utf-8')
except ImportError:
    import json
    def json_loads(s: str) -> Any: 
        return json.loads(s)
    def json_dumps(o: Any) -> str: 
        return json.dumps(o)
