import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCENARIO_RESEARCH = ROOT / "scenario_research"

if str(SCENARIO_RESEARCH) not in sys.path:
    sys.path.insert(0, str(SCENARIO_RESEARCH))
