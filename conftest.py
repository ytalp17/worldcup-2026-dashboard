"""Root conftest.py — ensures the WC2026 project root is first on sys.path
so that `import app` resolves to this project's app.py, not any other
app.py that may exist in sibling directories on sys.path.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Insert project root at index 0 so our app.py wins over any sibling project.
_project_root = str(Path(__file__).parent)
if _project_root in sys.path:
    sys.path.remove(_project_root)
sys.path.insert(0, _project_root)
