"""Makes the repository root importable so that `pytest` finds reproduce.py.

Without this, plain `pytest` passes only when invoked as `python -m pytest`,
which happens to put the working directory on sys.path. That difference is
invisible locally and fails in CI.
"""
