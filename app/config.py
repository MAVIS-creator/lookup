from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
DB_PATH = ROOT_DIR / "phone_retention.db"
HOST = "127.0.0.1"
PORT = 8080
