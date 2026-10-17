"""Local configuration; never log API credentials."""
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".researcher"


def default_articles_path():
    rechecked = LOCAL / "articles_rechecked.json"
    return rechecked if rechecked.is_file() else LOCAL / "articles.json"


def configure():
    from crew_ai.framework import load_env
    load_env(str(ROOT / ".env"))
    LOCAL.mkdir(exist_ok=True)
    os.environ.setdefault("MLFLOW_TRACKING_URI", f"sqlite:///{LOCAL / 'mlflow.db'}")
    os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "false")
    os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "1")
    os.environ.setdefault("MLFLOW_SCORER_MAX_WORKERS", "1")
    import mlflow
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    if os.getenv("MLFLOW_EXPERIMENT_ID"):
        experiment = mlflow.get_experiment(os.environ["MLFLOW_EXPERIMENT_ID"])
        if experiment is None:
            raise ValueError("MLFLOW_EXPERIMENT_ID does not exist")
        mlflow.set_experiment(experiment_id=experiment.experiment_id)
    else:
        experiment = mlflow.set_experiment("functional-soda-researcher-pilot")
        os.environ["MLFLOW_EXPERIMENT_ID"] = experiment.experiment_id
    mlflow.openai.autolog()
    return experiment
