import os
import sys


def pytest_configure():
    """
    Ensure `import src.*` works when pytest is executed from repo root
    without installing the package.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

