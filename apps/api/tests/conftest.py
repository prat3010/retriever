import os
import sys

_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

_processing_core = os.path.join(_repo_root, "packages", "processing-core", "src")
if _processing_core not in sys.path:
    sys.path.insert(0, _processing_core)
