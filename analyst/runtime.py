"""Project-local CrewAI state, with noninteractive cloud-tracing opt-out."""
import json
import os
from pathlib import Path


def prepare_crewai_runtime():
    # CrewAI 1.6 first-run onboarding can prompt even when tracing=False.
    # Initialize only this project's state; preserve any existing preferences.
    storage = Path(os.environ["CREWAI_STORAGE_DIR"])
    storage.mkdir(parents=True, exist_ok=True)
    preference = storage / ".crewai_user.json"
    try:
        with preference.open("x") as handle:
            json.dump({"first_execution_done": True, "trace_consent": False}, handle)
    except FileExistsError:
        pass
