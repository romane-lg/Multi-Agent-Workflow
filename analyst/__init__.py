"""Company-specific analysis downstream of the frozen Researcher evidence pack."""
import os
from pathlib import Path

# Configure CrewAI before importing its runtime. Keep local state in the workspace
# and keep MLflow as the tracing destination rather than prompting for cloud traces.
os.environ.setdefault("CREWAI_STORAGE_DIR", str(Path(__file__).resolve().parents[1] / ".researcher" / "crewai"))
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
