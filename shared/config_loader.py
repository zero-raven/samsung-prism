"""
FinSight Config Loader
=======================
Loads finsight config.yaml and provides workspace path helpers.

Environment:
    FINSIGHT_HOME — Optional. Base path for all data I/O.
                    Defaults to a 'data/' directory next to this file's parent.
"""

import os
import yaml
from dotenv import load_dotenv

# Automatically load environment variables from .env file if it exists
load_dotenv()

_config = None
_finsight_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_finsight_root() -> str:
    """Return the root directory of the finsight package."""
    return _finsight_root


def get_data_dir() -> str:
    """
    Return the base data directory for all skill I/O.
    Uses FINSIGHT_HOME env var if set, otherwise defaults to <finsight_root>/data/
    """
    return os.environ.get("FINSIGHT_HOME", os.path.join(_finsight_root, "data"))


def get_workspace_path(*subdirs: str) -> str:
    """
    Build a path under the data directory.
    Example: get_workspace_path("queue", "pending_articles.yaml")
             → <data_dir>/queue/pending_articles.yaml
    """
    path = os.path.join(get_data_dir(), *subdirs)
    # Ensure parent directory exists
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    return path


def ensure_workspace():
    """Create all required data subdirectories if they don't exist."""
    dirs = ["queue", "events", "analysis", "graph", "portfolio",
            "briefing", "logs", "visualizations"]
    for d in dirs:
        os.makedirs(os.path.join(get_data_dir(), d), exist_ok=True)
    print(f"[Config] Workspace initialized at: {get_data_dir()}")


def load_config() -> dict:
    """
    Load and cache the finsight config.yaml.

    OUTPUT:
        dict — Full configuration dictionary
    """
    global _config
    if _config is None:
        config_path = os.path.join(_finsight_root, "config.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Config file not found at {config_path}. "
                f"Copy config.yaml to your finsight directory."
            )
        with open(config_path, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config


def read_yaml(filepath: str) -> dict:
    """Read a YAML file and return its contents as a dict."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data else {}


def write_yaml(filepath: str, data: dict):
    """Write a dict to a YAML file, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def append_to_log(message: str, log_name: str = "system.log"):
    """Append a timestamped message to a log file."""
    import datetime
    log_path = get_workspace_path("logs", log_name)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
