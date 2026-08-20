"""Retired as the process entry point (specs/002-web-frontend/research.md R7).

The single-tenant `CEOAgent()` this used to start unconditionally is now
constructed per-user, on demand, by `runtime/assistant_manager.py` — one
instance per signed-in user who has connected their own integrations and
clicked "Start" in the web UI, not one shared instance at process startup.

Run the API (which owns both the HTTP layer and the per-user runtime
manager) instead:

    uvicorn api.main:app --reload --port 8000
"""

import sys

if __name__ == "__main__":
    print(__doc__)
    sys.exit(1)
