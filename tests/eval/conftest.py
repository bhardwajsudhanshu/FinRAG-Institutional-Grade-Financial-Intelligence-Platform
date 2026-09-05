"""Test setup for tests/eval/. Adds the project root to sys.path so
`from finrag...` imports work without a full package install.
"""

import sys
from pathlib import Path

# tests/eval/conftest.py -> tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
