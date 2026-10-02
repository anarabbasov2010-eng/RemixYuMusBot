import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8609012191"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "vvpse")
DB_PATH = Path(os.getenv("DB_PATH", "/app/storage/remix.db"))
TMP_DIR = Path(os.getenv("TMP_DIR", "/tmp/remixyumus"))
TMP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
FREE_DAILY = 3
REF_BONUS = 3
