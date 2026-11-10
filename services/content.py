import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8"))

def domain_lessons(domain_id):
    return [lesson for lesson in load("lessons") if lesson["domain_id"] == domain_id]
