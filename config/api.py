"""
COMPONENT : API
PURPOSE   : Every value of the API that is safe to change live during the demo, in one place.
INPUTS    : environment variables (optional overrides)
OUTPUTS   : constants imported by src/api/main.py
DEPENDS ON: nothing
PANEL NOTE: One file to edit during the demo; restart the server and the change is live.
"""
import os

# DEMO-KNOB: True = API serves fixture answers (src/api/mocks.py) instead of calling lang/retrieval/answer.
# Flip to False once the real components are merged at integration (PLAN §5.3, 2:45).
USE_MOCKS = os.getenv("USE_MOCKS", "true").lower() == "true"

# DEMO-KNOB: True = serve cached demo answers, no LLM call (Wi-Fi-off safety net on stage).
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"

# DEMO-KNOB: which browser origins may call the API. "*" is fine for a local demo, not for production.
CORS_ORIGINS = ["*"]

# DEMO-KNOB: words that make the MOCK API return a refusal, so the UI can build its refusal state.
MOCK_REFUSAL_KEYWORDS = ["passport", "income tax", "income-tax"]
