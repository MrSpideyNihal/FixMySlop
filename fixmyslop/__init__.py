"""FixMySlop package bootstrap.

This keeps legacy absolute imports like `import macros` and
`from cli.cli_app import app` working when installed from PyPI.
"""

from pathlib import Path
import sys


_PKG_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PKG_DIR.parent

# Ensure sibling top-level modules/packages are importable in packaged installs.
if str(_PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(_PROJECT_ROOT))

