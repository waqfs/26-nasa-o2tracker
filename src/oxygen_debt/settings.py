"""Portable public snapshots and optional external research data."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get('OXYGEN_DATA_ROOT', PROJECT_ROOT/'data')).resolve()
SNAPSHOT_ROOT = PROJECT_ROOT/'data'

def read_json(relative):
    import json
    return json.loads((SNAPSHOT_ROOT/relative).read_text(encoding='utf-8'))
