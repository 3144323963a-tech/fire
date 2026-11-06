from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_DIR / "web"
NETWORK_ASSETS_DIR = WEB_DIR / "assets" / "networks"
DATA_DIR = Path(__file__).resolve().parent / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
DISPATCHES_FILE = DATA_DIR / "dispatches.json"
SAMPLE_DATA_DIR = PROJECT_DIR / "sample_data"
ENVIRONMENT_FILE = SAMPLE_DATA_DIR / "environment.json"
HOST = "127.0.0.1"
PORT = 8000
